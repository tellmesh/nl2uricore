# nl2uricore

Generator `*.markpact.md` z promptu naturalnego i prefixu URI.

## Deterministyczny fallback

```bash
nl2uricore generate \
  --prompt "Stwórz URI pack cache:// do statusu i komendy run" \
  --prefix cache \
  --no-llm \
  --out /tmp/uricache.markpact.md
```

## Pełna ścieżka

```bash
nl2uricore generate --prefix printer --no-llm \
  --prompt "Stwórz URI pack printer:// do statusu, testu dysz i czyszczenia głowicy." \
  --out markpacts/packs/uriprinter.generated.markpact.md

urisys markpact validate markpacts/packs/uriprinter.generated.markpact.md
urisys markpact test markpacts/packs/uriprinter.generated.markpact.md
urisys --packs none --markpact markpacts/packs/uriprinter.generated.markpact.md \
  call printer://epson/query/status
```

LiteLLM (`--model`) można podłączyć później — domyślnie dostępny jest generator regułowy `--no-llm`.


## License

Licensed under Apache-2.0.
