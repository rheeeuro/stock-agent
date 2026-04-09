"use client";

function DigitReel({
  digit,
  animate,
  delay,
}: {
  digit: number;
  animate: boolean;
  delay: number;
}) {
  return (
    <span
      className="inline-block overflow-hidden"
      style={{ height: "1em", lineHeight: "1em", verticalAlign: "bottom" }}
    >
      <span
        className="inline-flex flex-col"
        style={{
          transform: `translateY(${-digit}em)`,
          transition: animate
            ? `transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`
            : "none",
        }}
      >
        {Array.from({ length: 10 }, (_, n) => (
          <span
            key={n}
            className="block"
            style={{ height: "1em", lineHeight: "1em" }}
          >
            {n}
          </span>
        ))}
      </span>
    </span>
  );
}

interface SlotNumberProps {
  value: string;
  animate: boolean;
  className?: string;
}

export function SlotNumber({ value, animate, className }: SlotNumberProps) {
  let digitIndex = 0;

  return (
    <span
      className={`inline-flex items-end ${className ?? ""}`}
      style={{ fontVariantNumeric: "tabular-nums", lineHeight: "1em", height: "1em" }}
    >
      {value.split("").map((char, i) => {
        if (/\d/.test(char)) {
          const delay = digitIndex * 60;
          digitIndex++;
          return (
            <DigitReel
              key={i}
              digit={parseInt(char)}
              animate={animate}
              delay={delay}
            />
          );
        }
        return (
          <span key={i} style={{ lineHeight: "1em" }}>
            {char}
          </span>
        );
      })}
    </span>
  );
}
