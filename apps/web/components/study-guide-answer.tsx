"use client";

import { parseStudyGuideCards } from "../app/page-model";

export function StudyGuideAnswer({ answer }: { answer: string }) {
  const cards = parseStudyGuideCards(answer);
  if (!cards.length) {
    return <div className="answer">{answer}</div>;
  }

  return (
    <div className="study-guide-cards">
      {cards.map((card, index) => (
        <details className="guide-card" key={`${card.title}-${index}`} open={index === 0}>
          <summary>
            <span>Question {index + 1}</span>
            <strong>{card.title}</strong>
          </summary>
          <div className="guide-card-body">
            {card.body.length ? (
              card.body.map((line, lineIndex) => <p key={`${card.title}-${lineIndex}`}>{line}</p>)
            ) : (
              <p>No generated answer body was returned for this question.</p>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}
