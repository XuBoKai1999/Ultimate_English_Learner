# Article Analysis Prompt

## Task

Analyze the cleaned English article you just produced for English-learning purposes.

Your job is to:

1. choose one existing Category;
2. select words, phrases, and chunks worth noticing;
3. classify each selected item by learning value.

Do not create vocabulary cards at this stage.

Return only valid JSON matching the schema below.

## Category

Choose exactly one:

| Category                       | Scope                                                        |
| ------------------------------ | ------------------------------------------------------------ |
| `Physics & Mathematics`        | Physics, mathematics, astronomy, cosmology, complex systems  |
| `Medicine & Life Science`      | Medicine, health, biology, evolution, ecology                |
| `Psychology & Mind`            | Psychology, Jungian psychology, dreams, memory, consciousness, cognition, parapsychology |
| `Philosophy & Ideas`           | Philosophy, philosophy of mind, philosophy of science, ethics, epistemology |
| `Religion, Myth & Esotericism` | Religion, mythology, mysticism, ritual, alchemy, folklore, esotericism |
| `History & Anthropology`       | History, archaeology, anthropology, civilizations, social class |
| `AI & Technology`              | AI, LLMs, computing, technology, engineering                 |
| `Society & World`              | Society, population, education, politics, international affairs |
| `Economics & Finance`          | Economics, finance, investing, business, industry            |
| `Literature & Culture`         | Fiction, essays, literature, literary criticism, art, culture |
| `Uncategorized`                | Material that does not reasonably fit another category       |

Choose the category that best represents the article as a whole.

Use `Uncategorized` only when no existing category fits reasonably well.

Do not create new categories.

## Vocabulary Selection

Select useful vocabulary from the article.

Items may be:

- `word`: an individual word;
- `phrase`: a multi-word expression;
- `chunk`: a reusable language pattern or lexical chunk.

Be selective. Do not extract every unfamiliar or difficult-looking word.

Prefer vocabulary that is useful for understanding or learning English.

Preserve a multi-word expression when learning it as a unit is more useful than extracting its individual words.

## Learning Level

Classify every selected item as exactly one of:

### `general`

Generally useful English, including common academic, formal, news, or broadly reusable vocabulary and expressions.

### `domain`

Vocabulary associated with a particular field but common enough within that field to be worth recognizing.

### `specialized`

Highly specialized terminology that a non-specialist is unlikely to encounter often.

Specialized terminology may still be selected when it is important for understanding the article. Do not treat technical appearance alone as a reason to select an item.

## Output

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

## Requirements

- Use the article title when available.
- Select exactly one Category.
- Every item must occur in the cleaned article you just produced.
- Do not duplicate the same item.
- Do not generate definitions, translations, examples, notes, scores, IDs, or learning-state data.
- Return JSON only.
