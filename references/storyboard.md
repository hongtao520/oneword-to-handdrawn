# Storyboard schema

Create UTF-8 JSON at `<project>/storyboard.json`:

```json
{
  "title": "狐假虎威",
  "language": "zh",
  "scenes": [
    {
      "id": "01",
      "caption": "从前，一只老虎在森林里\n抓住了一只狐狸。",
      "narration": "从前，一只老虎在森林里抓住了一只狐狸。",
      "image": "images/01.png",
      "visual": "狐狸被老虎拦住，森林小路，角色全身入画"
    }
  ]
}
```

Rules:

- Use zero-padded, unique scene IDs in display order.
- Keep `caption` to 1–3 lines and roughly 14 Chinese characters per line.
- Use `\n` to control caption lines.
- Keep one complete spoken sentence in `narration`.
- Preserve user-supplied wording unless they ask for rewriting.
- Set `image` to a project-relative PNG, JPG, JPEG, BMP, or TIFF path.
- Keep `visual` concrete and imageable; it guides image generation but is not rendered.
- Prefer 6–8 scenes for a short story. Split at real narrative turns.
- Do not put duration in the storyboard. The build derives it from narration in voiced mode
  and readable text length in silent mode.
