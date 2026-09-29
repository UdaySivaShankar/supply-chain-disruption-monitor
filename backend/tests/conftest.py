import pytest
import pytest_asyncio
import re
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from models import Base, Supplier, InventoryItem, PurchaseOrder, DisruptionCase
from models.supplier import SupplierStatus
from models.purchase_order import POStatus
from models.disruption_case import DisruptionType, Severity, DisruptionStatus
from database.connection import get_db
import main as main_module
from main import app
from httpx import AsyncClient, ASGITransport
import uuid
from datetime import datetime, timezone, timedelta

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# StaticPool keeps every session on the single in-memory connection so the
# background agent workflow (which opens its own sessions) sees the same
# database as the API request session.
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class FakeHindsightStore:
    """In-memory stand-in used only in tests.

    It mirrors the two Hindsight operations the application calls (retain and
    recall) so the learning loop can be asserted without a running Hindsight
    service. Production code always talks to the real Hindsight client.
    """

    def __init__(self):
        self.memories = []
        self.retain_calls = []
        self.recall_calls = []

    def retain(self, bank_id: str, content: str) -> dict:
        memory = {
            "id": str(uuid.uuid4()),
            "bank_id": bank_id,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memories.append(memory)
        self.retain_calls.append(memory)
        return memory

    def recall(self, bank_id: str, query: str, limit: int = 5) -> list:
        self.recall_calls.append({"bank_id": bank_id, "query": query, "limit": limit})
        terms = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 3}
        scored = []
        for memory in self.memories:
            hits = sum(1 for term in terms if term in memory["content"].lower())
            if hits:
                scored.append((hits, memory))
        scored.sort(key=lambda pair: -pair[0])
        return [
            dict(memory, relevance_score=min(0.99, 0.6 + 0.1 * hits))
            for hits, memory in scored[:limit]
        ]


@pytest.fixture
def hindsight_store():
    return FakeHindsightStore()


@pytest_asyncio.fixture(autouse=True)
async def isolated_environment(db_session, monkeypatch, hindsight_store):
    """Route every long-running dependency at the test doubles.

    - The background LangGraph workflow and the disruption services open their
      own database sessions, so they are pointed at the test engine.
    - Hindsight retain/recall are pointed at the in-memory fake so no network
      call is attempted and so tests can assert what was remembered.
    """
    import api.routes.disruptions as disruptions_route
    import agents.mitigation as mitigation_module
    import services.disruption_service as disruption_service_module

    monkeypatch.setattr(disruptions_route, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(mitigation_module, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(disruption_service_module, "AsyncSessionLocal", TestSessionLocal)

    # Production code calls the async client variants (aretain/arecall) so the
    # event loop stays free; the fakes are synchronous, so they are wrapped.
    def as_async(fake):
        async def wrapper(*args, **kwargs):
            return fake(*args, **kwargs)

        wrapper.__name__ = getattr(fake, "__name__", "hindsight_fake")
        return wrapper

    monkeypatch.setattr(disruptions_route, "aretain", as_async(hindsight_store.retain))
    monkeypatch.setattr(mitigation_module, "arecall", as_async(hindsight_store.recall))
    monkeypatch.setattr(main_module, "arecall", as_async(hindsight_store.recall))

    yield hindsight_store


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_supplier(db_session):
    supp = Supplier(
        name="Test Metals Corp",
        country="India",
        city="Mumbai",
        contact_email="test@metals.com",
        lead_time_days=10,
        reliability_score=0.92,
        capabilities=["steel", "aluminum"],
        status=SupplierStatus.active,
    )
    db_session.add(supp)
    await db_session.commit()
    await db_session.refresh(supp)
    return supp


@pytest_asyncio.fixture
async def sample_alt_supplier(db_session):
    supp = Supplier(
        name="Global Steel GmbH",
        country="Germany",
        city="Stuttgart",
        contact_email="orders@globalsteel.de",
        lead_time_days=7,
        reliability_score=0.96,
        capabilities=["steel", "iron"],
        status=SupplierStatus.active,
    )
    db_session.add(supp)
    await db_session.commit()
    await db_session.refresh(supp)
    return supp


@pytest_asyncio.fixture
async def sample_inventory_item(db_session, sample_supplier):
    item = InventoryItem(
        name="Grade A Steel Sheet",
        sku="SKU-STEEL-001",
        category="Raw Metal",
        current_quantity=500.0,
        unit="tonnes",
        daily_demand_rate=25.0,
        safety_stock=50.0,
        reorder_point=100.0,
        primary_supplier_id=sample_supplier.id,
        unit_cost=800.0,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def sample_purchase_order(db_session, sample_supplier, sample_inventory_item):
    po = PurchaseOrder(
        order_number="PO-TEST-001",
        supplier_id=sample_supplier.id,
        inventory_item_id=sample_inventory_item.id,
        quantity=250.0,
        unit_cost=800.0,
        total_cost=200000.0,
        status=POStatus.in_transit,
        order_date=datetime.now(timezone.utc) - timedelta(days=5),
        expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=5),
    )
    db_session.add(po)
    await db_session.commit()
    await db_session.refresh(po)
    return po
