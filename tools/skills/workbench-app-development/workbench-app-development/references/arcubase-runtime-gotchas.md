# Arcubase Runtime Gotchas

Read this reference before writing datetime row values or defining `serialnumber` fields. These rules guard current direct-write behavior that is not fully described by the schema reference. If a newer CLI contract explicitly differs, stop, verify it with a minimal read-back, and update this reference instead of guessing.

## Datetime row writes

Send datetime field values as finite integer epoch seconds. Do not send date-only and ISO strings directly, and do not send epoch milliseconds; the current write path can accept those values while storing the wrong instant.

- Establish the intended timezone before converting an input without one.
- Route every datetime create/update value through one tested `toEpochSeconds` helper.
- Keep ISO/RFC3339 strings as display/read values only; convert them again before a later write.
- After the first datetime write for an app, read the first record back and compare the stored instant with the intended value. Stop on any mismatch before bulk writes.

A TypeScript boundary helper may use this shape:

```ts
export function toEpochSeconds(value: string | Date): number {
  const milliseconds = value instanceof Date ? value.getTime() : Date.parse(value);
  if (!Number.isFinite(milliseconds)) throw new Error("Invalid datetime value");
  return Math.floor(milliseconds / 1000);
}
```

Do not pass numeric timestamps through without first distinguishing epoch seconds from epoch milliseconds.

## Serial number fields

Use only serial parts and option values supported by the current CLI help and field reference. Do not guess `perdefinedFormat`, `format`, or other undocumented date-part values.

If the requested identifier includes a date prefix and current evidence cannot implement it:

1. Stop before saving the schema.
2. Ask whether to keep investigating the exact date format or change the business identifier.
3. Use the following six-digit, non-resetting fallback only when the developer explicitly accepts a pure global serial:

```json
{
  "type": "serialnumber",
  "options": {
    "parts": [{
      "mode": "buildin",
      "type": "serial",
      "options": {
        "length": 6,
        "lenfixed": true,
        "random": false,
        "reset": "no"
      }
    }]
  }
}
```

Never silently replace a date-prefixed identifier with this fallback. After saving the chosen schema, create and read back one record to verify the rendered serial before depending on it.
