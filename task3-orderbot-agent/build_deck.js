const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/708a4b49-29cc-4341-8296-62b14d701e3a_297e0a2b-f5ae-485e-a7ce-a73013faa174/pptx/scripts/apply_theme.js");

const THEME = {
  name: "OrderBot",
  headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1F2933", lt1: "FFFFFF", dk2: "3E4C59", lt2: "F3F5F7",
    accent1: "1E8E5A", accent2: "C8372D", accent3: "6B7785", accent4: "F2A900",
    accent5: "0F766E", accent6: "9AA5B1", hlink: "0F766E", folHlink: "6B7785" },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";           // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "OrderBot: automating hardware order processing";
pres.author = "Graduate Developer, Datacom";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "TITLE_ONLY", background: { color: C.background1 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.75,
    fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } }],
  slideNumber: { x: 9.2, y: 5.25, color: C.accent3, fontFace: THEME.bodyFontFace, fontSize: 10 },
});

const FONT = THEME.bodyFontFace;
function box(s, name, x, y, w, h, text, o = {}) {
  s.addText(text, { objectName: name, shape: o.shape || pres.ShapeType.roundRect, rectRadius: 0.08, x, y, w, h,
    fill: { color: o.fill || C.text2 }, line: o.line ? { color: o.line, width: 1.5 } : { type: "none" },
    color: o.color || C.background1, fontFace: FONT, fontSize: o.size || 12, bold: o.bold !== false,
    align: "center", valign: "middle", margin: 0.05, isTextBox: true });
}
function arrow(s, x1, y1, x2, y2, color) {
  s.addShape(pres.ShapeType.line, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1, line: { color, width: 2, endArrowType: "triangle" } });
}
function badge(s, n, x, y, color) {
  s.addText(String(n), { objectName: "Badge " + n, shape: pres.ShapeType.ellipse, x, y, w: 0.3, h: 0.3,
    fill: { color }, line: { type: "none" }, color: C.background1, fontFace: FONT, fontSize: 11, bold: true,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}

// 5-step row shared by slides 1 and 2 so the before/after reads at a glance
const XS = [0.5, 2.35, 4.2, 6.05, 7.9], W = 1.55, Y = 1.45, H = 0.85;
function row(s, labels, fill, arrowColor) {
  labels.forEach((t, i) => {
    if (i < 4) box(s, "Step " + (i + 1), XS[i], Y, W, H, t, { fill });
    if (i < 4) arrow(s, XS[i] + W, Y + H / 2, XS[i + 1], Y + H / 2, arrowColor);
  });
  box(s, "Decision", XS[4], 1.3, W, 1.15, labels[4], { fill: C.background2, color: C.text1, line: arrowColor, shape: pres.ShapeType.diamond });
}

// ---------------- Slide 1: the problem ----------------
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("Our order process is a bottleneck", { placeholder: "title" });
  s.addText("Today: every hardware order is handled by hand", { objectName: "Subtitle", x: 0.5, y: 1.0, w: 9, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 14, color: C.accent3, isTextBox: true });
  row(s, ["Email with PDF order form", "Staff read the PDF and re-type it", "Check customer in Salesforce", "Check stock in Google Sheet", "All OK?"], C.text2, C.accent3);
  badge(s, 1, XS[1] + W - 0.15, Y - 0.15, C.accent2);
  badge(s, 2, XS[2] + W - 0.15, Y - 0.15, C.accent2);
  badge(s, 2, XS[3] + W - 0.15, Y - 0.15, C.accent2);
  // branches
  arrow(s, XS[4] + W / 2, 2.45, 7.2, 3.0, C.accent3);
  arrow(s, XS[4] + W / 2, 2.45, 8.85, 3.0, C.accent3);
  s.addText("Yes", { objectName: "Yes label", x: 6.55, y: 2.55, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText("No", { objectName: "No label", x: 9.05, y: 2.55, w: 0.4, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  box(s, "Yes branch", 6.35, 3.0, 1.7, 1.0, "Write 2 emails by hand: customer and warehouse", { fill: C.text2, size: 11 });
  box(s, "No branch", 8.2, 3.0, 1.3, 1.0, "Email sales rep, then wait", { fill: C.accent2, size: 11 });
  badge(s, 3, 8.2 + 1.3 - 0.15, 3.0 - 0.15, C.text1);
  // pain points
  const pains = [
    ["Manual re-typing", "Order details copied from PDF by hand, so typos and wrong items slip in"],
    ["Slow, repeated checks", "Two systems checked one after the other for every order"],
    ["Problems stall orders", "Questions go back by email and the order waits for a reply"],
  ];
  pains.forEach((p, i) => {
    const y = 3.0 + i * 0.68;
    s.addText(String(i + 1), { objectName: "Pain badge " + (i + 1), shape: pres.ShapeType.ellipse, x: 0.5, y: y + 0.05, w: 0.32, h: 0.32,
      fill: { color: i === 2 ? C.text1 : C.accent2 }, line: { type: "none" }, color: C.background1, fontFace: FONT, fontSize: 12, bold: true,
      align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: p[0], options: { bold: true, color: C.text1, breakLine: true } }, { text: p[1], options: { color: C.accent3 } }],
      { objectName: "Pain point " + (i + 1), x: 0.95, y, w: 5.1, h: 0.6, fontFace: FONT, fontSize: 12, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("Also: orders wait whenever staff are away. Timings are estimates to be confirmed with Operations.", { objectName: "Footnote", x: 0.5, y: 5.1, w: 8.5, h: 0.3,
    fontFace: FONT, fontSize: 10, italic: true, color: C.accent3, margin: 0, isTextBox: true });
  s.addNotes("Walk the flow left to right. Every grey box is a person doing a manual step; the red numbers mark where errors and delays creep in. The 'No' branch is the worst: the order just waits for an email reply. Timings are estimates, so confirm real volumes and handling times with Operations before quoting numbers.");
}

// ---------------- Slide 2: the solution ----------------
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("Meet OrderBot, our autonomous AI agent", { placeholder: "title" });
  s.addText("Same steps, done automatically in minutes, 24/7", { objectName: "Subtitle", x: 0.5, y: 1.0, w: 9, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 14, color: C.accent3, isTextBox: true });
  row(s, ["Order email arrives", "OrderBot reads the PDF", "Checks customer in Salesforce", "Checks stock in Google Sheet", "All OK?"], C.accent1, C.accent1);
  arrow(s, XS[4] + W / 2, 2.45, 7.2, 3.0, C.accent1);
  arrow(s, XS[4] + W / 2, 2.45, 8.85, 3.0, C.accent1);
  s.addText("Yes", { objectName: "Yes label", x: 6.55, y: 2.55, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText("No", { objectName: "No label", x: 9.05, y: 2.55, w: 0.4, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.accent4, margin: 0, isTextBox: true });
  box(s, "Yes branch", 6.35, 3.0, 1.7, 1.0, "Emails customer and warehouse, updates stock and Salesforce", { fill: C.accent1, size: 11 });
  box(s, "No branch", 8.2, 3.0, 1.3, 1.0, "Asks rep for exactly what is missing, alerts a person", { fill: C.accent4, color: C.text1, size: 11 });
  const pts = [
    ["Reads", "every order email the moment it arrives"],
    ["Checks", "the customer and stock in seconds"],
    ["Decides", "routine orders alone; hands tricky ones to a person, with the reason"],
  ];
  pts.forEach((p, i) => {
    const y = 3.0 + i * 0.62;
    s.addText("✓", { objectName: "Check " + (i + 1), shape: pres.ShapeType.ellipse, x: 0.5, y: y + 0.03, w: 0.32, h: 0.32,
      fill: { color: C.accent1 }, line: { type: "none" }, color: C.background1, fontFace: FONT, fontSize: 12, bold: true,
      align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: p[0] + " ", options: { bold: true, color: C.text1 } }, { text: p[1], options: { color: C.text2 } }],
      { objectName: "How it works " + (i + 1), x: 0.95, y, w: 5.1, h: 0.55, fontFace: FONT, fontSize: 14, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("People stay in control: staff handle every exception, and every action is logged.", { objectName: "Footnote", x: 0.5, y: 4.95, w: 8.5, h: 0.3,
    fontFace: FONT, fontSize: 12, bold: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes("Same five steps as the previous slide, so the audience can compare. OrderBot is an AI agent: it is given a goal (process each order from email to confirmation in under 5 minutes at 99.5% accuracy) and uses tools to read email and PDFs, query Salesforce and the Google Sheet, and send emails. When something is missing or unclear it does not guess; it asks the sales rep exactly what is needed and flags a person.");
}

// ---------------- Slide 3: impact and next steps ----------------
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("Faster orders, fewer errors, low-risk start", { placeholder: "title" });
  const tiles = [
    ["< 5 min", "order to confirmation (target), down from hours"],
    ["99.5%", "accuracy target, checked before go-live"],
    ["24/7", "no waiting for someone to be at their desk"],
    ["More time", "staff freed for customers and tricky orders"],
  ];
  tiles.forEach((t, i) => {
    const x = 0.5 + (i % 2) * 2.4, y = 1.3 + Math.floor(i / 2) * 1.6;
    s.addShape(pres.ShapeType.roundRect, { objectName: "Tile " + (i + 1), x, y, w: 2.2, h: 1.45, rectRadius: 0.08, fill: { color: C.background2 }, line: { type: "none" } });
    s.addText(t[0], { objectName: "Tile number " + (i + 1), x: x + 0.12, y: y + 0.1, w: 1.96, h: 0.6, fontFace: THEME.headFontFace, fontSize: i === 3 ? 22 : 30, bold: true, color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(t[1], { objectName: "Tile label " + (i + 1), x: x + 0.12, y: y + 0.75, w: 1.96, h: 0.62, fontFace: FONT, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  });
  s.addShape(pres.ShapeType.roundRect, { objectName: "PoC card", x: 5.45, y: 1.3, w: 4.05, h: 3.05, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.accent1, width: 1.5 } });
  s.addText("Next step: a read-only Proof of Concept", { objectName: "PoC heading", x: 5.65, y: 1.4, w: 3.65, h: 0.55, fontFace: THEME.headFontFace, fontSize: 16, bold: true, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
  const steps = [
    ["Watch", "OrderBot reads real orders but changes nothing"],
    ["Compare", "its decisions against what staff actually did"],
    ["Decide", "go or no-go on a phased rollout, based on measured accuracy"],
  ];
  steps.forEach((p, i) => {
    const y = 2.05 + i * 0.75;
    s.addText(String(i + 1), { objectName: "Step badge " + (i + 1), shape: pres.ShapeType.ellipse, x: 5.65, y: y + 0.03, w: 0.32, h: 0.32,
      fill: { color: C.accent1 }, line: { type: "none" }, color: C.background1, fontFace: FONT, fontSize: 12, bold: true,
      align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: p[0] + ": ", options: { bold: true, color: C.text1 } }, { text: p[1], options: { color: C.text2 } }],
      { objectName: "PoC step " + (i + 1), x: 6.1, y, w: 3.2, h: 0.65, fontFace: FONT, fontSize: 13, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("Our ask: approve a 4-week read-only pilot. No risk to live orders.", { objectName: "Ask band", shape: pres.ShapeType.roundRect, rectRadius: 0.08,
    x: 0.5, y: 4.6, w: 9, h: 0.6, fill: { color: C.text1 }, line: { type: "none" }, color: C.background1, fontFace: FONT, fontSize: 16, bold: true,
    align: "center", valign: "middle", margin: 0.1, isTextBox: true });
  s.addNotes("Figures are targets from the project brief, not measured results; the pilot exists to prove them. Read-only means OrderBot cannot send emails or edit Salesforce or the inventory sheet, so there is no risk to live orders. The 4-week length is a proposal to agree with Operations.");
}

(async () => {
  await pres.writeFile({ fileName: "OrderBot_Presentation.pptx" });
  await applyTheme("OrderBot_Presentation.pptx", THEME);
  console.log("written");
})();
