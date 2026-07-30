# Asset inventory

`assets.tsv` is the flat provenance record for files extracted during the first organization pass. `copied-source-preserved` means the target was copied and SHA-256 matched while the original remained untouched; `inventory-only-not-copied` means the large installer remains only at its old path.

Trust labels are important:

- `prototype-dummy-labels`: the DHP19 loader returns zero-filled 3D pose labels and is not trainable ground truth.
- `invalid-openeb-format-demo` and `not-openeb-raw`: the custom byte format is not a valid OpenEB RAW stream.
- `fabricated-output-demo`: the script prints predefined benchmark numbers and is not evidence of measured filtering performance.
- `ai-generated-unverified`: historical setup notes may be useful context, but only `docs/setup` is treated as verified guidance.

Renaming a target does not change its bytes. Original and target paths plus SHA-256 make every extracted file traceable without recreating old source folder trees.
