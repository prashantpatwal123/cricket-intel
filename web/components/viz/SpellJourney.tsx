"use client";
// Spell Journey: one column per over the bowler bowled; each ball is a cell. Spells are grouped; wickets highlighted.
import { OUTCOME_COLOR, symbolToOutcome } from "@/lib/viz/model";

export default function SpellJourney({ story, sel, onSel }: { story: any; sel: string | null; onSel: (b: any) => void }) {
  const overs = story.overs as any[];
  const maxR = Math.max(12, ...overs.map((o) => o.runs));
  return (
    <div className="spellj">
      {overs.map((o, i) => {
        const newSpell = i === 0 || overs[i - 1].spell_no !== o.spell_no;
        return (
          <div key={o.over} className={`sp-over ${newSpell && i ? "gap" : ""}`}>
            {newSpell && <div className="sp-label">Spell {o.spell_no}</div>}
            <div className="sp-head"><b>{o.over + 1}</b><span className="mini">{o.state.score}{o.state.required_rate ? ` · need ${o.state.required_rate.toFixed(1)}` : ""}</span></div>
            <div className="sp-runs" title={`${o.runs} runs`}><i style={{ height: `${(100 * o.runs) / maxR}%` }} /></div>
            <div className="sp-sum"><b className="num">{o.runs}</b>{o.wickets ? <span className="wk"> {o.wickets}w</span> : null}</div>
            <div className="sp-balls">
              {o.balls_list.map((b: any) => {
                const oc = symbolToOutcome(b.symbol);
                return <button key={b.delivery_id} className={`sp-ball ${sel === b.delivery_id ? "on" : ""} ${b.wicket ? "w" : ""}`}
                  style={{ background: b.wicket ? "#ff5c74" : oc ? OUTCOME_COLOR[oc] + "40" : "#ffb54733" }} onClick={() => onSel(b)}
                  title={`${b.ball_label}: ${b.symbol} to ${b.batter}`}>{b.symbol}</button>;
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
