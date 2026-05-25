import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";

type Doc = {
  id: number;
  file_name: string;
  file_type: string;
  status: string;
  is_demo?: boolean;
};

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.documents.list().then((d) => setDocs(d as Doc[])).finally(() => setLoading(false));
  }, []);

  const add = () => {
    api.documents
      .create({ file_name: "new_document.pdf", file_type: "other", status: "missing" })
      .then(() => api.documents.list().then((d) => setDocs(d as Doc[])));
  };

  if (loading) return <Loading />;

  return (
    <div>
      <div className="flex justify-between mb-6">
        <h2 className="text-2xl font-display text-hive-gold">Document Vault</h2>
        <button className="btn-primary" onClick={add}>
          Add metadata
        </button>
      </div>
      <p className="text-sm text-hive-muted mb-4">
        File upload storage is TODO — metadata tracking works for MVP checklist.
      </p>
      {docs.length === 0 ? (
        <EmptyState title="No documents" />
      ) : (
        <div className="grid gap-3">
          {docs.map((d) => (
            <div key={d.id} className="card flex justify-between items-center">
              <div>
                <p className="font-medium">{d.file_name}</p>
                <p className="text-xs text-hive-muted">{d.file_type}</p>
              </div>
              <div className="flex gap-2 items-center">
                {d.is_demo && <span className="badge bg-purple-500/20 text-purple-300">demo</span>}
                <StatusBadge status={d.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
