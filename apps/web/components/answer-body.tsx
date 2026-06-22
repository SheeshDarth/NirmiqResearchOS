export function AnswerBody({ answer }: { answer: string }) {
  const lines = answer.split("\n");
  return (
    <div className="answer structured-answer">
      {lines.map((rawLine, index) => {
        const line = rawLine.trim();
        if (!line) return <div className="answer-gap" key={`gap-${index}`} />;
        const isBullet = /^[-*]\s+/.test(line);
        const isHeading =
          !isBullet &&
          line.length <= 72 &&
          !/[.!?]$/.test(line) &&
          !/^\[\d+\]/.test(line) &&
          index !== lines.length - 1;
        if (isHeading) {
          return (
            <strong className="answer-heading" key={`${line}-${index}`}>
              {line.replace(/^#+\s*/, "")}
            </strong>
          );
        }
        if (isBullet) {
          return (
            <p className="answer-bullet" key={`${line}-${index}`}>
              {line.replace(/^[-*]\s+/, "")}
            </p>
          );
        }
        return <p key={`${line}-${index}`}>{line}</p>;
      })}
    </div>
  );
}
