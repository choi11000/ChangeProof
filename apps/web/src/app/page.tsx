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

        <form className="analysis-card">
          <div className="field wide">
            <label htmlFor="repository">GitHub repository</label>
            <input id="repository" placeholder="https://github.com/acme/risky-saas" type="url" />
          </div>
          <div className="field">
            <label htmlFor="pr">Pull request</label>
            <input id="pr" min="1" placeholder="42" type="number" />
          </div>
          <button type="submit">Analyze change <span>→</span></button>
        </form>

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
        <div className="score-card">
          <div><small>BEFORE</small><strong>87</strong><span className="high">HIGH</span></div>
          <span className="arrow">→</span>
          <div><small>AFTER FIX</small><strong>12</strong><span className="low">LOW</span></div>
        </div>
      </section>
    </main>
  );
}
