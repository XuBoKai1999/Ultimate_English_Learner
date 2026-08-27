# Vocabulary Card Generation Prompt

## Task

Generate vocabulary cards using the cleaned article and the analysis JSON you produced earlier in this conversation.

Use the most recently produced analysis JSON to determine which items to process.

Use the cleaned article from earlier in this conversation to determine their contextual meanings and usage.

Generate all cards in one response.

Return only valid JSON matching the schema below.

## Input

### Cleaned Article Context

Use the cleaned original English article produced earlier in this conversation.

Use it as the primary source of context.

### Previous Analysis JSON

Expected structure:

```json
{
  "title": "string",
  "category": "string",
  "items": [
    {
      "text": "string",
      "type": "word | phrase | chunk",
      "level": "general | domain | specialized"
    }
  ]
}
```

Generate exactly one card for every item in `items`.

## Card Content

For each item:

- preserve `text`;
- preserve `type`;
- preserve `level`;
- give a concise Traditional Chinese meaning appropriate to the article context;
- provide one natural English example sentence;
- provide a Traditional Chinese translation of that example.

The example should clearly demonstrate the relevant meaning and normal usage. It must be a natural, complete sentence suitable for full-sentence dictation.

Apart from the target word, phrase, or chunk, prefer common and easy-to-understand English. Avoid unnecessary rare vocabulary and specialist terminology.

Use the original article sentence only when it is clear and suitably concise for learning and dictation. If it is overly complex, create a simpler natural sentence with the same relevant meaning.

## Output

Produce one batch JSON file:

```json
{
  "cards": [
    {
      "text": "string",
      "type": "word | phrase | chunk",
      "level": "general | domain | specialized",
      "meaning_zh": "string",
      "example_en": "string",
      "example_zh": "string"
    }
  ]
}
```

## Requirements

- Generate exactly one card for every item in the previous analysis JSON.
- Preserve the order of the previous analysis JSON.
- Do not add, remove, merge, or split items.
- Preserve `text`, `type`, and `level`.
- Interpret meanings according to the cleaned article.
- Use Traditional Chinese.
- Keep meanings concise.
- Keep examples natural and useful for learning.
- Make every `example_en` a complete sentence suitable for full-sentence dictation.
- Do not generate IDs, filenames, paths, categories, dates, audio information, review state, or other application metadata.
- Do not split the output into separate card files. The application will perform that step.
- Return JSON only.
