/**
 * Original Buzzle plush bee: rounded wings, honey body and soft cocoa details.
 * Authored SVG geometry; no imported artwork. See docs/brand-mark.md.
 */
export function Bee({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 120 110" fill="none" aria-hidden="true" focusable="false" data-brand-mark="voice-note-bee">
      <ellipse cx="60" cy="101" rx="25" ry="4" fill="#CDA655" opacity=".12"/>
      {/* Rounded petal wings, with a subtle inset instead of a hard outline. */}
      <path d="M42 53C25 55 14 44 19 31c5-12 21-6 26 7l5 15Z" fill="#FFFDF6" stroke="#DCCBA8" strokeWidth="2"/>
      <path d="M75 51c0-16 9-28 20-23 14 7 8 26-11 30Z" fill="#FFFDF6" stroke="#DCCBA8" strokeWidth="2"/>
      <path d="M26 33q-4 8 6 14m59-12q5 7-4 14" stroke="#F0E7D3" strokeWidth="3" strokeLinecap="round"/>
      <path d="M48 32q-1-10-8-13m31 13q2-10 9-13" stroke="#8C6944" strokeWidth="3" strokeLinecap="round"/>
      <circle cx="39" cy="18" r="4.5" fill="#A58153"/><circle cx="81" cy="18" r="4.5" fill="#A58153"/>
      {/* Squashy silhouette and warm layered shading keep the mark crisp when small. */}
      <path d="M60 28c23 0 35 17 35 38 0 21-13 33-35 33S25 87 25 66c0-21 12-38 35-38Z" fill="#E7B64E"/>
      <path d="M60 28c21 0 33 16 33 35 0 19-12 31-33 31S27 82 27 63c0-19 12-35 33-35Z" fill="#FFDA76"/>
      <path d="M43 37q-7 3-10 12" stroke="#FFF0BD" strokeWidth="5" strokeLinecap="round"/>
      <path d="M35 77q25 10 50 0m-42 12q17 5 34 0" stroke="#A27A45" strokeWidth="6" strokeLinecap="round"/>
      {/* Little hands, rosy cheeks and bright eyes. */}
      <ellipse cx="29" cy="72" rx="6" ry="9" transform="rotate(-23 29 72)" fill="#FFE395"/>
      <ellipse cx="91" cy="72" rx="6" ry="9" transform="rotate(23 91 72)" fill="#FFE395"/>
      <ellipse cx="42" cy="65" rx="7" ry="4.5" fill="#EDA18D" opacity=".7"/>
      <ellipse cx="78" cy="65" rx="7" ry="4.5" fill="#EDA18D" opacity=".7"/>
      <ellipse cx="46" cy="56" rx="3.7" ry="4.8" fill="#674D35"/>
      <ellipse cx="74" cy="56" rx="3.7" ry="4.8" fill="#674D35"/>
      <circle cx="47" cy="54.5" r="1.2" fill="#FFFDF5"/><circle cx="75" cy="54.5" r="1.2" fill="#FFFDF5"/>
      <path d="M55 65q5 7 10 0" stroke="#795137" strokeWidth="2.6" strokeLinecap="round"/>
    </svg>
  );
}
