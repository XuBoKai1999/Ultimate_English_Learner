# Article Cleaning Prompt

## Task

From the raw text provided earlier in this conversation, identify the actual article and extract only its meaningful article content.

Preserve the original wording. Do not summarize, translate, simplify, or rewrite.

Remove content that is not part of the article itself, including surrounding webpage, email, navigation, promotional, or interface text.

Preserve the article's meaningful structure when identifiable:

- title;
- subtitle;
- author and date;
- headings;
- paragraphs;
- quotations;
- lists;
- meaningful captions.

Repair obvious formatting damage from copying, such as broken paragraphs, unnecessary line breaks, duplicated whitespace, or stray interface fragments.

When uncertain whether a passage belongs to the article, decide from context and retain it only if it contributes to the article's content.

## Output

Return only the cleaned article in Markdown.

Do not add commentary, explanations, summaries, metadata blocks, or code fences.
