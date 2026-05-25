import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";

const FIELDS: { key: string; label: string; rows?: number }[] = [
  { key: "personal_details", label: "Personal details", rows: 3 },
  { key: "education", label: "Education" },
  { key: "university", label: "University" },
  { key: "major", label: "Major" },
  { key: "visa_status", label: "Visa status" },
  { key: "gpa", label: "GPA" },
  { key: "financial_need", label: "Financial need", rows: 3 },
  { key: "projects", label: "Projects", rows: 3 },
  { key: "achievements", label: "Achievements", rows: 3 },
  { key: "leadership", label: "Leadership", rows: 2 },
  { key: "volunteering", label: "Volunteering", rows: 2 },
  { key: "career_goals", label: "Career goals", rows: 3 },
  { key: "personal_statements", label: "Reusable personal statements", rows: 4 },
  { key: "scholarship_preferences", label: "Scholarship preferences", rows: 3 },
];

export default function Profile() {
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.profile.get().then((p) => {
      setForm(p as Record<string, unknown>);
      setLoading(false);
    });
  }, []);

  const save = () => {
    api.profile.update(form).then(() => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    });
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Profile Vault</h2>
      <div className="card max-w-3xl space-y-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!!form.international_student}
            onChange={(e) => setForm({ ...form, international_student: e.target.checked })}
          />
          International student
        </label>
        {FIELDS.map((f) => (
          <div key={f.key}>
            <label className="text-sm text-hive-muted block mb-1">{f.label}</label>
            {f.rows ? (
              <textarea
                className="input-field"
                rows={f.rows}
                value={String(form[f.key] ?? "")}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
              />
            ) : (
              <input
                className="input-field"
                value={String(form[f.key] ?? "")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    [f.key]: f.key === "gpa" ? parseFloat(e.target.value) || null : e.target.value,
                  })
                }
              />
            )}
          </div>
        ))}
        <button className="btn-primary" onClick={save}>
          {saved ? "Saved ✓" : "Save profile"}
        </button>
      </div>
    </div>
  );
}
