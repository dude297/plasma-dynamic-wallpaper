# Wallpaper library

The library commands install checksum-verified HEIC files into the current
user's XDG data directory, normally:

```text
~/.local/share/dynamic-wallpaper/wallpapers/
```

Browse and search the catalog:

```bash
dynamic-wallpaper --library-list
dynamic-wallpaper --library-search mountain
```

Install, inspect, and remove wallpapers:

```bash
dynamic-wallpaper --library-install example-id
dynamic-wallpaper --library-installed
dynamic-wallpaper --library-remove example-id
```

After installation, set `HEIC_FILE` in
`~/.config/dynamic-wallpaper/config` to the path printed by the command.

## Catalog source

The default catalog is maintained separately from the application. For local
catalog development or mirrors, override it with:

```bash
PDW_CATALOG_URL=file:///absolute/path/catalog.json \
  dynamic-wallpaper --library-list
```

The environment variable also accepts an HTTPS URL.

## Catalog format

```json
{
  "wallpapers": [
    {
      "id": "example",
      "name": "Example Wallpaper",
      "author": "Example Author",
      "description": "A short description.",
      "download_url": "https://example.org/example.heic",
      "sha256": "64-lowercase-hexadecimal-characters",
      "filename": "example.heic"
    }
  ]
}
```

Every entry requires an HTTPS or `file://` download URL and SHA-256 checksum.
Downloads are written atomically and rejected if their checksum differs from
the catalog.

Catalog maintainers must publish only files they are authorized to distribute.
