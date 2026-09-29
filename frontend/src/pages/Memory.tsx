import React, { useEffect, useState } from 'react';
import { BrainCircuit } from 'lucide-react';
import { api } from '../api/api';
import { HindsightMemory } from '../api/types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function Memory() {
  const [memories, setMemories] = useState<HindsightMemory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getMemories()
      .then(setMemories)
      .catch(err => setError(err.message || 'Failed to load memories'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Hindsight Long-Term Memory</h2>
        <p className="mt-2 text-slate-600 bg-white p-4 rounded-md border border-slate-200">
          Hindsight stores past disruption experiences, decisions, and outcomes. When a new disruption occurs, relevant memories are retrieved and shown to agents to improve recommendations.
        </p>
      </div>

      <div className="space-y-4">
        {memories.map((mem, idx) => (
          <div key={mem.id || idx} className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
            <div className="flex items-start mb-2">
              <BrainCircuit className="w-5 h-5 text-accent-blue mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <span className="inline-block bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded uppercase tracking-wider mb-2">
                  [HINDSIGHT MEMORY]
                </span>
                <p className="text-slate-700 leading-relaxed">{mem.content}</p>
                {mem.retrieved_at && (
                  <p className="mt-3 text-xs text-slate-400">Stored/Retrieved: {new Date(mem.retrieved_at).toLocaleString()}</p>
                )}
              </div>
            </div>
          </div>
        ))}
        {memories.length === 0 && (
          <div className="bg-white p-12 text-center rounded-md border border-slate-200 text-slate-500">
            No memories stored yet. Resolve a disruption to store the experience.
          </div>
        )}
      </div>
    </div>
  );
}
