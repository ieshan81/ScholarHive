import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";
import { ConfigBanner } from "../components/ConfigBanner";

type Essay = {
  id: number;
  scholarship_id?: number;
  prompt?: string;
  draft_text?: string;
  final_text?: string;
  word_count: number;
  authenticity_score: number;
  status: string;
  is_demo?: boolean;
  review_suggestions?: string[];
};

export default function Essays() {
  const [essays, setEssays] = useState<Essay[]>([]);
  const [scholarships, setScholarships] = useState<{ id: number; name: string }[]>([]);
  const [geminiOk, setGeminiOk] = useState(true);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Essay | null>(null);

  useEffect(() => {
    Promise.all([api.essays.list(), api.scholarships.list(), api.health()])
      .then(([e, s, h]) => {
        setEssays(e as Essay[]);
        setScholarships(s as { id: number; name: string }[]);
        setGeminiOk(!!h.gemini_configured);
      })
      .finally(() => setLoading(false));
  }, []);

  const generate = async (sid: number) => {
    try {
      await api.essays.generate(sid);
      const e = await api.essays.list();
      setEssays(e as Essay[]);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Generation failed");
    }
  };

  const review = async (id: number) => {
    const r = await api.essays.review(id);
    const e = await api.essays.list();
    setEssays(e as Essay[]);
    setSelected((e as Essay[]).find((x) => x.id === id) || null);
    alert(`Personal Voice Review: ${r.message}\nScore: ${r.authenticity_score}`);
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Essay Studio</h2>
      <p className="text-sm text-hive-muted mb-4">
        Drafts pull from Memory Vault automatically. Personal Voice Review improves truthfulness — not detector evasion.
      </p>
      {!geminiOk && (
        <ConfigBanner message="Gemini not configured — drafts require GEMINI_API_KEY" />
      )}

      <div className="card mb-6">
        <h3 className="font-semibold mb-2">Generate draft</h3>
        <select
          className="input-field max-w-md"
          onChange={(e) => e.target.value && generate(Number(e.target.value))}
          defaultValue=""
        >
          <option value="">Select scholarship...</option>
          {scholarships.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
        </select>
      </div>

      {essays.length === 0 ? (
        <EmptyState title="No essays drafted yet" hint="Evaluate a scholarship in Radar, then generate a draft here." />
      ) : (
        <div className="grid gap-4">
          {essays.map((e) => (
            <div key={e.id} className="card">
              <div className="flex justify-between items-start">
                <div>
                  <StatusBadge status={e.status} />
                  <p className="text-sm text-hive-muted mt-2">{e.word_count} words · Auth: {e.authenticity_score}%</p>
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary text-sm" onClick={() => review(e.id)}>
                    Personal Voice Review
                  </button>
                  <select
                    className="input-field text-xs py-1 max-w-[160px]"
                    defaultValue=""
                    onChange={(ev) => {
                      if (ev.target.value) {
                        api.essays.rewrite(e.id, ev.target.value).then(() => api.essays.list().then((x) => setEssays(x as Essay[])));
                        ev.target.value = "";
                      }
                    }}
                  >
                    <option value="">Rewrite mode…</option>
                    <option value="more_specific">More specific</option>
                    <option value="more_natural">More natural</option>
                    <option value="add_story_evidence">Add story evidence</option>
                    <option value="reduce_generic">Reduce generic wording</option>
                    <option value="tighten_word_count">Tighten word count</option>
                    <option value="align_prompt">Align to prompt</option>
                    <option value="keep_voice">Keep my voice</option>
                  </select>
                  <button
                    className="btn-primary text-sm"
                    onClick={() => api.essays.approve(e.id).then(() => api.essays.list().then(setEssays))}
                  >
                    Approve
                  </button>
                </div>
              </div>
              <p className="text-xs text-hive-muted mt-2 line-clamp-2">{e.prompt}</p>
              <button className="text-sm text-hive-accent mt-2" onClick={() => setSelected(e)}>
                Edit draft
              </button>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="card max-w-2xl w-full">
            <h3 className="font-semibold mb-2">Edit essay</h3>
            <textarea
              className="input-field h-48"
              defaultValue={selected.final_text || selected.draft_text}
              id="essay-edit"
            />
            <div className="flex gap-2 mt-4">
              <button
                className="btn-primary"
                onClick={() => {
                  const el = document.getElementById("essay-edit") as HTMLTextAreaElement;
                  api.essays
                    .update(selected.id, { draft_text: el.value, final_text: el.value })
                    .then(() => {
                      setSelected(null);
                      api.essays.list().then(setEssays);
                    });
                }}
              >
                Save
              </button>
              <button className="btn-secondary" onClick={() => setSelected(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
