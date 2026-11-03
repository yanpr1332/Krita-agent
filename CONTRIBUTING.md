# Contributing

This project is in the planning stage. Discuss substantial changes in an issue before implementation where practical. Create a topic branch from `main` and submit a focused pull request. Describe the motivation, validation, and compatibility impact. Changes to `main` go through a pull request; resolve review conversations before merging. The branch protection applies to administrators as well.

## Documentation languages

`README.md` is the default English introduction and `README.zh-CN.md` is its Simplified Chinese counterpart. Keep their meaning, structure, links, and project status synchronized in the same pull request whenever either changes. Review both versions for omissions and stale claims. Other repository documentation is maintained in English.

## Validation and compatibility

- Record the actual Krita build and acceptance results for changes involving Krita. A symbol found in upstream source is not proof that an installed build supports it.
- Add meaningful automated tests as implementation becomes available, and document manual acceptance where a real Krita instance is required. Stable CI checks may later become required branch checks.
- Use isolated test documents and back up shared resources before deploying a plugin. Avoid committing artwork, credentials, personal configuration, or generated caches.
- Check licenses before adding dependencies or copying third-party material. Do not copy Krita source into this project without understanding its licensing implications.
