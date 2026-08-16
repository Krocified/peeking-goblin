1. title is too long. and the header is always in line with the search bar, even if on home view.
   FIXED: title shortened to "Peeking Goblin" (one line, `white-space: nowrap`). Home view header now stacks above the search bar (`.topline` is a plain grid column; only the compact view puts header and search inline).
2. in condensed view, the title is too long. causing a second line. also, no spacing between header and Choose a card to continue. (status or loading text)
   FIXED: compact title is a single-line clamp(22px, 3vw, 32px); status line now has `margin: 20px 0 0` so there is breathing room between the header and the status/loading text.
3. Ambiguous search doesnt need to be explicitly rendered.
   FIXED: removed the "Ambiguous search" / "Suggested match" eyebrow from the candidate picker; kept the "Choose the card" heading, helper text, and result count.
4. No quick selection for pages. user must type or press next multiple times on multipage results.
   FIXED: replaced the page number input + Go button with a `<select>` dropdown listing "Page N of T"; picking an option jumps directly.
5. spacing issues in the pagination controller
   FIXED: `.candidate-pagination` gets `gap: 12px`, `margin-top: 16px`, consistent bottom padding, and the page select is styled/min-height to match the buttons.
6. in card view, english text is too small. previously, it is shown in a separate line under the card header.
   FIXED: english text is no longer buried in a collapsed `<details>` toggle; it renders as a full-size (15px, 1.6 line-height) paragraph on its own line under the card header.
7. filters are too scuffed. make it a dropdown, and clear button for each should be an X in each dropdown field.
   FIXED: rarity/set filters are now single-select dropdowns (with an "All" default) instead of multi-select list boxes; each field shows an × clear button inside it when a filter is active. "Clear all filters" still resets everything. Note: multi-select per filter was dropped in favor of single-select dropdowns.
8. cant click on the header to go back to home
   FIXED: in compact view the header is clickable (cursor + "Back to home" tooltip); clicking aborts any in-flight request and resets to the home view.
