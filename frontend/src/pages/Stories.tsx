import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";

type Story = {
  id: number;
  title: string;
  category: string;
  tags?: string;
  summary?: string;
  verified_by_user: boolean;
  used_in_essays_count: number;
  is_demo?: boolean;
};

const CATEGORIES = [
  "financial challenge",
  "leadership",
  "engineering project",
  "family background",
  "failure and recovery",
  "community service",
  "academic growth",
  "international student experience",
];

export default function Stories() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => api.stories.list().then((d) => setStories(d as Story[])).finally(() => setLoading(false));

  useEffect(() => {
    load();
  }, []);

  const add = () => {
    api.stories
      .create({
        title: "New story",
        category: "engineering project",
        summary: "",
        verified_by_user: false,
      })
      .then(load);
  };

  if (loading) return <Loading />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-display text-hive-gold">Story Bank</h2>
        <button className="btn-primary" onClick={add}>
          Add story
        </button>
      </div>
      {stories.length === 0 ? (
        <EmptyState title="No stories saved yet" hint="Add real personal stories you can verify for essay reuse." />
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {stories.map((s) => (
            <div key={s.id} className="card">
              <div className="flex gap-2 items-center">
                <h3 className="font-semibold">{s.title}</h3>
                {s.is_demo && <span className="badge bg-purple-500/20 text-purple-300">demo</span>}
              </div>
              <p className="text-xs text-hive-gold mt-1">{s.category}</p>
              {s.tags && <p className="text-xs text-hive-muted mt-1">{s.tags}</p>}
              <p className="text-sm mt-2 line-clamp-3">{s.summary}</p>
              <div className="flex gap-2 mt-3 text-xs">
                <span
                  className={
                    s.verified_by_user
                      ? "text-emerald-400"
                      : "text-amber-400"
                  }
                >
                  {s.verified_by_user ? "✓ Verified" : "Unverified"}
                </span>
                <span className="text-hive-muted">Used in {s.used_in_essays_count} essays</span>
              </div>
              <button
                className="btn-secondary text-xs mt-3"
                onClick={() =>
                  api.stories
                    .update(s.id, { verified_by_user: !s.verified_by_user })
                    .then(load)
                }
              >
                Toggle verified
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
