import { AnalysisForm } from "@/components/analysis-form";

const stages = ["Understand", "Dependencies", "Validate", "Evidence", "Remediate"];

export default function Home() {
  return (
    <main>
      <nav aria-label="Primary navigation">
        <a className="brand" href="#top">ChangeProof</a>
        <span className="status"><i /> Systems ready</span>
      </nav>

      <section className="hero" id="top">
        <p className="eyebrow">DATABASE CHANGE RISK AGENT</p>
        <h1>Prove a change is safe<br /><span>before it ships.</span></h1>
        <p className="lede">
          ChangeProof turns pull-request changes into validated evidence, deterministic risk,
          and a remediation you can verify.
        </p>

        <ol className="judge-flow" aria-label="Three-step proof flow">
          <li><b>1</b> Analyze the change</li>
          <li><b>2</b> Reproduce the failure</li>
          <li><b>3</b> Verify the fix</li>
        </ol>

        <AnalysisForm />

        <ol className="pipeline" aria-label="Analysis pipeline">
          {stages.map((stage, index) => (
            <li key={stage}><b>{String(index + 1).padStart(2, "0")}</b>{stage}</li>
          ))}
        </ol>
      </section>

      <section className="proof">
        <article>
          <p className="eyebrow">DETERMINISTIC BY DESIGN</p>
          <h2>Reasoning makes a hypothesis.<br />Evidence earns the verdict.</h2>
        </article>
        <div className="principle-card">
          <small>CURRENT CAPABILITY</small>
          <strong>PR → structured change facts</strong>
          <p>No invented risk score. Every fact starts with source we can inspect.</p>
        </div>
      </section>
    </main>
  );
}
