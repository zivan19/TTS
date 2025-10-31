# TTS

## Chunking

The project includes a punctuation- and paragraph-aware chunker (`tts_edge.chunking.chunk_text`) that
produces text segments suitable for incremental text-to-speech processing. The chunker:

- Normalizes whitespace, removes control characters, and collapses runs of blank lines.
- Detects paragraphs first and then sentences, preferring NLTK or spaCy for sentence boundaries and
  falling back to a carefully tuned regular expression when those libraries are unavailable.
- Avoids splitting inside numbers and URLs by only cutting at confident sentence endings.
- Packs sentences into chunks that target a configurable size (default ~2.5k characters) while
  allowing ±10% tolerance so that whole sentences stay intact.
- Preserves paragraph breaks where possible by respecting blank-line boundaries.

When generating text, aim for paragraphs separated by blank lines to give the chunker natural break
points. If you are processing exceptionally long sentences (for example, bullet lists without
punctuation), consider inserting sentence-ending punctuation periodically; otherwise the chunker will
return the entire sentence as a single chunk to avoid partial splits.
