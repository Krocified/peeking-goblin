import "./Brand.scss";

export default function Brand({
  compact,
  onHome,
}: {
  compact: boolean;
  onHome: () => void;
}) {
  return (
    <header
      className="brand"
      onClick={compact ? onHome : undefined}
      title={compact ? "Back to home" : undefined}
    >
      <p className="eyebrow">Yugioh OCG / market lens</p>
      <h1>
        Peeking <em>Goblin</em>
      </h1>
      {!compact && (
        <p className="lede">
          Type a card name in English. We'll peek live prices quickly. OCG
          prices are from Yuyu-tei. AE prices are from TCG Corner.
        </p>
      )}
    </header>
  );
}
