# Cog Spec v0.1

**Status:** Public discussion draft

**Stability:** Experimental; this is not yet the official 0.1 release

## Purpose

This is the adopt-now definition of a Cog.

The goal of v0.1 is to make Cogs concrete enough that someone can write one,
share it, inspect it, and load it into an AI system without first adopting a
particular runtime, model provider, marketplace, or hosting product.

If people can create several useful Cogs from this document and implementations
can recognize the same artifacts, v0.1 is doing its job.

Being precise about the scope of that job: v0.1 makes a Cog **recognizable,
inspectable, and self-identifying**. It does not yet make two Cogs written
against different manifest schemas **interoperable**, because it does not define
what a manifest contains. That is deliberate — the shape should follow
implementation experience rather than precede it — and `manifest_schema` exists
so the gap is visible rather than silent.

This draft is intentionally small. It standardizes the Cog artifact, not the
complete system that may operate it.

Implementations and application profiles may add stricter packaging, runtime,
publication, or marketplace requirements without changing what qualifies as a
Cog under this core specification.

## Definition

A **Cog** is a portable, installable AI worker: a durable role and work
contract, the context that grounds it, and — where the Cog carries one — the
model that performs the work.

A Cog describes:

- what kind of worker it is;
- what work it is intended to perform;
- the guidance it should follow;
- the inputs and context it expects;
- the outputs it should produce; and
- the boundaries of its responsibility.

A Cog is more than a prompt because it represents a reusable worker identity and
contract, packaged so that what it needs is stated rather than assumed. It may
include or reference models, tools, Skills, Frames, memory configuration,
evaluation material, and other resources.

A Cog is not, merely by being loaded or installed, a running process, account,
deployment, or grant of authority.

## Relationship to related artifacts

### Skills

A Skill provides reusable guidance for performing a particular kind of task. A
Cog may use one or more Skills while carrying a broader worker identity and
responsibility.

A runtime activates a Skill within an existing worker when its guidance is
relevant. A runtime instantiates a Cog as the worker itself.

The difference is structural, not only semantic. A Skill is guidance handed to a
worker that already exists, and it says nothing about what that worker needs. A
Cog is a directory that declares, in a manifest, what it requires and what it
carries — which is what makes it something an implementation can resolve,
depend on, and install rather than merely read.

`COG.md` deliberately follows the familiar Markdown-and-frontmatter convention
used by Agent Skills, so the two are pleasant to author side by side. What
differs is not that file but what surrounds it.

### Frames

A Frame provides context, norms, terminology, or constraints that apply to
work. A Cog may work under one or more Frames.

### Models and runtimes

A model supplies inference. A Cog does not need to contain a model, or the
software that executes one, in order to conform to v0.1.

A Cog **may** carry them. A Cog that includes model weights and an inference
runtime is a conforming Cog, and installing it makes that model available on the
installing system. So is a Cog that carries only context and expects a model to
be supplied from elsewhere. Both are ordinary cases rather than exceptions.

A richer package or application profile may declare model requirements, bind the
Cog to a model or provider, and define the runtime support needed to operate it.
Such packaging is compatible with this specification even though those
declarations are not standardized by the v0.1 core.

CogSpec v0.1 does not define how a runtime selects a model, grants tools,
assembles context, stores memory, or executes work.

## File format

A Cog is a directory. Its entry file is named `COG.md`, and that file names the
manifest:

```text
my-cog/
├── COG.md          # Required: the entry file
├── cog.yaml        # Required: the manifest named by `manifest` (any format)
├── skills/         # Optional: bundled or referenced Skills
├── frames/         # Optional: bundled or referenced Frames
├── references/     # Optional: supporting documentation
├── evaluation/     # Optional: examples, fixtures, or results
├── assets/         # Optional: templates and other resources
└── ...             # Other implementation-specific files
```

Only `COG.md` and the manifest it names are required. The subdirectories are
conventions rather than separately standardized package types.

`cog.yaml` is shown only because it is the conventional filename. The manifest
may use any format and any name; `COG.md` says which file it is. See
[Manifest](#manifest).

An extension profile may require a more specific layout or additional package
contents. Additional files do not make a conforming Cog non-conforming.

### Drafts

A `COG.md` written on its own, before a manifest exists, is a **draft**. It is a
useful thing to write and share — it states the work contract in a single
readable file, and every line of it survives unchanged when the manifest is
added. Promoting a draft is adding `manifest:`, `manifest_schema:`, and the
file they name — nothing else.

It is not yet a Cog. A loose Markdown file declares nothing: it names no
capability, requires nothing, offers no interface, and carries no model. Nothing
can resolve it against an environment, depend on it, or install it. It can only
be read, or pasted into something that already has a model.

A draft is nonetheless a defined artifact rather than a scratch file, because
tooling consumes it. The most direct case is a Cog that builds Cogs: it takes a
draft as input — the work contract, which is the part a person must author — and
produces the manifest, schemas, examples, and directory structure around it. For
that to work the draft has to be recognizable and its required fields
dependable, which is what `type`, `name`, and `description` provide.

This is also why a draft does not need to declare what it requires. Anything
structured enough to be worth declaring is what a Cog-creating tool derives or
elicits; putting it in the draft would do that work in a weaker place.

Earlier drafts of this specification treated the single-file form as a Cog in its
own right. That followed from an earlier conception of a Cog as a text artifact.
Under the definition above — an installable worker — a file with no manifest is
the beginning of a Cog rather than one.

A validator given a loose `COG.md` should check what it can and report the
subject as a draft, not as a conforming Cog.

## Cog file contents

The Cog Markdown file contains YAML frontmatter followed by a Markdown body.

```markdown
---
type: cog [0.1]
name: repository-risk-analyst
description: Reviews repository dependency evidence and produces a prioritized, evidence-referenced risk brief.
---

# Repository Risk Analyst

You are a repository risk analyst...
```

The frontmatter provides lightweight metadata used to recognize and describe
the Cog. The Markdown body contains the worker definition and instructions.

The frontmatter is YAML, but deliberately only a small part of it. Which shapes
and which syntax are available is defined in
[What belongs in the frontmatter](#what-belongs-in-the-frontmatter), and applies
to every field below — those this specification names and those it does not.

## Required frontmatter

Every v0.1 Cog has these fields:

| Field | Meaning |
|---|---|
| `type` | Identifies the file as a Cog |
| `name` | Short machine-readable name |
| `description` | What the Cog does and when it should be used |
| `manifest` | Relative path to the Cog's machine-readable manifest |
| `manifest_schema` | Identifier for the shape that manifest follows |

`manifest` and `manifest_schema` are a pair. Neither is meaningful alone: the
first says where the manifest is, the second says what it claims to be.

### `type`

The value is exactly:

```yaml
type: cog
```

or, to declare this specification version, exactly:

```yaml
type: cog [0.1]
```

The versioned form is recommended for public or shared Cogs.

The general Cog-family grammar is:

```text
^cog( \[[0-9]+\.[0-9]+\])?$
```

The values accepted for v0.1 conformance are:

```text
^cog( \[0\.1\])?$
```

An implementation handles type values as follows:

- `cog` is a valid unversioned Cog;
- `cog [0.1]` is a valid v0.1 Cog;
- another well-formed version, such as `cog [0.2]`, may be recognized as a Cog
  but must not be reported as conforming to v0.1; and
- any other value is invalid for v0.1.

### `name`

`name` is a short machine-readable name.

It:

- must be 1–64 characters;
- may contain lowercase ASCII letters, numbers, and hyphens;
- must not begin or end with a hyphen; and
- must not contain consecutive hyphens.

The Cog's directory should normally have the same name as the Cog.

Examples:

```yaml
name: repository-risk-analyst
```

```yaml
name: project-manager
```

### `description`

`description` is a short explanation of what the Cog does and when it should be
used.

It:

- must be non-empty;
- must be no more than 1,024 characters; and
- should be understandable without reading the complete body.

Example:

```yaml
description: Reviews dependency evidence for a repository snapshot and produces a prioritized risk brief for engineering leaders.
```

## Recommended frontmatter

The following fields are optional but useful:

| Field | Meaning |
|---|---|
| `kind` | Where the Cog's inference comes from: `model`, `context`, or `complete` |
| `version` | Version of this Cog |
| `publisher` | The identity releasing this Cog |
| `license` | License name or reference to a bundled license file |
| `homepage` | Human-readable page describing the Cog |
| `repository` | Where its source is maintained |
| `metadata` | Additional string key-value metadata |

A Cog that is publicly distributed or intended for repeated installation
should include `kind`, `version`, `publisher`, and `license`. An application
profile may make these or other optional fields mandatory for its own purposes
without making them required for basic CogSpec conformance.

Example:

```yaml
kind: context
version: "0.1.0"
publisher: Example Organization
license: Apache-2.0
homepage: https://example.org/cogs/repository-risk-analyst
repository: https://github.com/example/repository-risk-analyst
metadata:
  category: software-risk
  maturity: experimental
```

### What belongs in the frontmatter

The frontmatter answers *what is this, and may I use it*. The manifest answers
*how does it compose and run*.

Stated operationally: an index should be able to list, search, and filter a
catalog of Cogs by reading only the Markdown frontmatter, without parsing a
manifest whose format it may not support.

To keep that true, two rules apply. The first bounds the **shape** a value may
take:

> Frontmatter values are scalars, lists of scalars, or the `metadata` mapping of
> string keys to string values. A field that needs richer structure — a mapping
> other than `metadata`, a list of mappings, or a list of lists — belongs in the
> manifest instead.

The second bounds the **syntax** used to write it:

> Every value is written on the line of its key, except a list, which may
> instead be an indented block of single-line `- item` entries. A scalar is
> plain, single-quoted, or double-quoted. A list is a flow sequence in square
> brackets or such a block. YAML's remaining node syntax — block scalars (`|`
> and `>`), anchors and aliases (`&` and `*`), explicit tags (`!`), and values
> continued across lines — is outside CogSpec frontmatter.
>
> A field key is a plain scalar containing no whitespace. It ends at the first
> `:` followed by whitespace or end of line. `version`, `x-vendor`, `x.y`, and
> `example.org/thing` are all keys; a quoted key and a key containing a space
> are not. A key begins with an indicator character under the same rule that
> governs values below: never with `, [ ] { } & * ! | > ' " % @` or a backtick,
> and with `-`, `?`, or `:` only where no whitespace follows — which is why the
> line `- x: v` is a list entry rather than a field named `- x`.
>
> The frontmatter contains no tab characters. Indent with spaces, and write
> `\t` in a double-quoted scalar where a tab is the value.

Within those limits the syntax is YAML's own, with nothing further removed. A
double-quoted scalar may use any YAML escape, so `"a\tb"` and `"café"` are
ordinary values — an escape is single-line syntax and excluding it would refuse
valid frontmatter for no benefit.

The remaining rules are the places YAML itself is narrower than it first looks,
and each is a rule only because a parser would otherwise reject the line:

- A plain scalar may not **contain** `: ` or end in `:`, because YAML reads
  those as a mapping. A `:` not followed by whitespace is not an indicator,
  which is why `urn:example:thing` and `https://example.org/a` are plain
  scalars.
- A plain scalar may not **begin** with an indicator character —
  `, [ ] { } & * ! | > ' " % @` or a backtick — nor with `-`, `?`, or `:`
  followed by whitespace. `-foo` is a scalar; `- foo` is a list entry.
- Inside a flow sequence a plain item may not contain `?` or begin with `:`,
  because flow context reads both as structure. Quote the item.

Quote anything these rules exclude, and quote it in the frontmatter rather than
working around it — the value is unchanged, and the file stays loadable by
everything.

### Values that must be strings

A plain scalar that looks like a number, a boolean, null, or a date **is** one.
`version: 1.0` is a float, `name: no` is `false`, and `released: 2001-12-14` is
a date rather than the text of one. Which forms resolve this way differs between
YAML 1.1 and YAML 1.2 — `0o17`, `1e3`, `y` and `12:30` are among the values the
two versions read differently — and a Cog does not get to choose which YAML its
consumer runs.

> Where this specification requires a string, quote any value whose plain form
> could be read as a number, boolean, null, or timestamp under either YAML
> version.

This is why `version` is written `"0.1.0"` throughout this document. An
implementation should report an unquoted value of that shape where a string is
required, rather than resolve it and hope the next reader agrees.

The first rule is what stops the frontmatter growing into a second manifest. The
second is what lets a reader with no YAML implementation available decide, one
line at a time, whether it understands what it is looking at — and refuse
cleanly when it does not, rather than guess.

Both limits apply to the frontmatter alone. The manifest is bound by whatever
`manifest_schema` names, and the Markdown body is not YAML at all; a `>` or `|`
in prose means nothing. Frontmatter written this way remains ordinary YAML, so a
full YAML parser reads it correctly too — the subset restricts what an author
may write, never what a reader must accept. The converse also holds and is the
sharper guarantee: **frontmatter this specification accepts is valid YAML.** A
construct a YAML parser would reject is outside the subset even where no rule
above names it.

The practical consequence is that `description` stays a single line — meaning
the **source line**, which is what a line-at-a-time reader has to cope with.
A double-quoted `\n` is single-line source and decodes to a real newline, so the
*value* may contain one; only block scalars and values continued across lines are
excluded. Nothing here forbids a decoded newline.

Authors should still avoid one. `description` is the sentence an index displays,
and an index has nowhere to put a line break; the explanation it summarizes
belongs in the Markdown body, which has no limit of either kind. Where a field
genuinely needs multi-line text, that is a signal it belongs in the manifest or
the body rather than a signal to encode newlines into the frontmatter.

### `kind`

`kind` states **where the Cog's inference comes from**.

| Value | Carries a model | Carries task context |
|---|---|---|
| `model` | yes | no |
| `context` | no | yes |
| `complete` | yes | yes |

- `model` — carries a model and the software that executes it, and supplies
  inference to whatever calls it. It holds no task context of its own.
- `context` — carries the task context: instructions, schemas, references, and
  the boundaries of the work. It requires inference to be supplied from
  elsewhere.
- `complete` — carries both the task context and the model that performs it.

`kind` does **not** describe whether the Cog contains executable code. A Cog of
any kind may contain code, tools, and interfaces, and much of what a `context`
Cog offers may work with no model present at all. What a `context` Cog cannot do
without externally supplied inference is the work it declares.

This is the question a person or catalog asks before installing: *does this
bring its own model, or do I need to supply one?* v0.1 does not define how a
`context` Cog locates a model, or what a `model` Cog's inference interface looks
like. It only lets a Cog state which side of that line it is on.

### `publisher`

`publisher` identifies who released the Cog. It is the identity that provenance,
signatures, and support expectations attach to under any profile that defines
them, which is not the same thing as who wrote the text.

Earlier drafts of this specification used `author`. Implementations reading
older files may treat `author` as `publisher`.

### Version

`version` tracks the Cog's own revision, not the CogSpec version. Semantic
Versioning is recommended but not required by v0.1.

Quote version values, per
[Values that must be strings](#values-that-must-be-strings): unquoted, `1.0` is
a float and `1.0.0` is a string, so an unquoted version changes type as the Cog
is revised.

```yaml
version: "0.1.0"
```

A shared or repeatedly revised Cog should include a version. A local
experimental Cog may omit one.

### Metadata

`metadata` is a mapping from string keys to string values. Implementations may
use it for information not defined by CogSpec.

Metadata must not be treated as a portable permission, authority grant, or
required runtime behavior.

This restriction applies only to the core `metadata` field. A profile's manifest
may use whatever structure that profile defines.

A profile should not introduce nested frontmatter fields, and the shape and
syntax limits in
[What belongs in the frontmatter](#what-belongs-in-the-frontmatter) hold for the
fields a profile adds as well as the ones defined here. Structure a profile
needs belongs in the manifest it defines, where it is free of both limits.

## Manifest

A Cog carries a machine-readable manifest. `COG.md` says where it is and what
shape it follows:

```yaml
manifest: cog.yaml
manifest_schema: example.org/cog-package [0.1]
```

`COG.md` is the only file whose name and format this specification fixes.
Everything else it points at.

That is deliberate. Declarations that tooling reads need structure the Markdown
frontmatter should not carry, but fixing a single manifest format would
foreclose reasonable choices — YAML, TOML, JSON, CUE, or a section inside a file
the surrounding ecosystem already uses. A pointer costs one field and settles
none of those questions.

`manifest`:

- must be a relative path within the Cog directory;
- must not use an absolute path or escape the Cog root with `..` segments;
- must name a file that exists;
- must remain inside the Cog root **after symbolic links are resolved**, not
  only after lexical normalization; and
- should indicate its format by conventional file extension.

**CogSpec v0.1 does not define what the manifest contains.** It defines only
that a Cog has one, how to find it, and how it identifies itself. Whether the
manifest declares capabilities, interfaces, model requirements, tools,
permissions, or anything else is left to extension profiles, and different
profiles may define different manifests for the same Cog.

### `manifest_schema`

`manifest_schema` names the shape the manifest follows. It is an opaque
identifier to this specification: v0.1 defines no values, registers none, and
attaches no meaning to any of them.

It exists so that deferring the manifest's contents does not make them
undecidable. Without it, two Cogs following different conventions are
indistinguishable — a reader cannot tell whether it fails to understand a
manifest or is misreading one, and a convention that later wins has no migration
path because nothing ever said which was being spoken. With it, an implementation
can decline honestly:

> This Cog's manifest follows `example.org/cog-package [0.1]`, which I do not
> support.

It sits in the frontmatter rather than inside the manifest for two reasons. An
index needs to know which Cogs it can resolve without parsing a manifest whose
format it may not support — the same reason identity lives in the frontmatter.
And it keeps this specification's promise literal: the core never opens the
manifest, yet can still say what dialect it is in.

Values should be namespaced and versioned. Communities and vendors define their
own; this specification arbitrates none of them, and names none of them.

Examples in this document use `example.org/…` deliberately. A specification that
shipped a particular vendor's identifier in its examples would make that
identifier look privileged, and would seed it into every Cog written by copying
the example. The arrow points the other way: a schema's own documentation says
which specification it serves.

### When the manifest's contents might be specified

Deferring is not abandoning. A candidate shape should normally be considered for
standardization when two independently built implementations resolve each
other's Cogs, and the shape they had to agree on is what gets written down —
consistent with the bar in [Relationship to future versions](#relationship-to-future-versions).

A core v0.1 validator does not read the manifest. It confirms that the field is
present, that the path is safe, and that the target exists. An implementation
that does not understand a manifest's format or contents can still read the
Cog's frontmatter and body, and should report that it did not interpret the
manifest rather than proceeding as though it had.

The manifest is not authority. Its presence, contents, or claims do not grant a
Cog access to anything.

## Markdown body

The Markdown body states the Cog's work contract in human-readable form: what the
work is, how to approach it, and where its boundaries lie. It is what a person
reads to decide whether to install the Cog and what to expect from it.

The body is one component among several — the manifest, the context, and any
bundled model are equally part of the Cog, and none of them is *the* definition
on its own.

v0.1 does not require fixed headings or a machine-readable body schema.

A useful Cog body should normally explain:

- role and purpose;
- supported work;
- unsupported work;
- expected inputs and context;
- expected outputs;
- instructions or working method;
- boundaries, refusals, and escalation behavior;
- completion criteria;
- known limitations; and
- examples when they improve understanding.

These are authoring recommendations, not required sections. Authors should
include only what helps a person or AI system understand and operate the worker.

The body should be readable without proprietary tooling.

## File references

A Cog may link to supporting files using ordinary relative Markdown links:

```markdown
Follow the [review method](references/review-method.md).

Use the [risk brief template](assets/risk-brief.md).
```

References are resolved relative to the Cog root. They MUST NOT use
absolute filesystem paths or escape the bundle root with `..` path segments.

A missing relative target should produce a warning unless an implementation can
determine that the target is required. CogSpec v0.1 does not require validators
to infer the meaning or necessity of every Markdown link.

Implementations may load references progressively instead of loading the entire
directory at once.

## Installation

A Cog is installed when a runtime makes its definition and supported resources
available for use. Installation may include validation, reference resolution,
compatibility checks, registration, and runtime-specific configuration.

Installation does not require a Cog to contain its own model or runtime. It
does not guarantee that a particular runtime can execute the Cog, and it does
not grant tools, credentials, data access, network access, or authority.

A runtime may refuse to install or execute a valid Cog when it cannot satisfy
the Cog's declared requirements or the requirements of an applicable profile.
That refusal does not make the Cog invalid under the core specification.

## Extension profiles

An extension profile defines additional requirements for a particular kind of
package, runtime, registry, marketplace, or other application of Cogs.

A profile may:

- require fields that are optional in the core specification;
- define additional frontmatter fields or structured manifests;
- require additional files or a particular bundle layout;
- define model, interface, tool, permission, memory, safety, or evaluation
  declarations;
- define installation, compatibility, integrity, provenance, or distribution
  rules; and
- define publication, marketplace, or commercial requirements.

A profile may impose stricter validation for artifacts claiming conformance to
that profile. It must not redefine the meaning of core CogSpec fields as they
appear in the Cog Markdown frontmatter, treat loading or installation as an
authority grant, or present profile-specific behavior as a guarantee of the
v0.1 core.

An artifact can therefore conform to both CogSpec v0.1 and one or more richer
profiles. Failure to satisfy a profile does not make an otherwise conforming
Cog invalid under CogSpec v0.1.

## Skills and Frames

A Cog may bundle or reference Skills and Frames.

CogSpec v0.1 does not require a particular reference field or resolution
mechanism. Authors may use relative Markdown links, URIs, names understood by a
particular implementation, or optional metadata.

The `skills/` and `frames/` directories are conventional locations only. Their
presence does not activate their contents. A Cog body or
implementation-specific metadata must reference them, and the implementation
determines how supported references are resolved.

An implementation should disclose how it resolves references and what happens
when a referenced artifact is unavailable.

## Visibility and access

CogSpec v0.1 does not define visibility, access control, or distribution policy.
Implementations may record those properties in `metadata` or in surrounding
systems. They are not portable authority or sharing guarantees in v0.1.

## Tools, permissions, and authority

CogSpec v0.1 does not standardize tool declarations, permission vocabularies,
approval workflows, or authority grants.

A Cog's text may describe tools it expects or actions it must not take, but
textual statements are not machine-enforced permissions.

At a minimum, an implementation must follow this rule:

> Installing a Cog does not grant it access to any tool, data source,
> credential, network destination, or external action.

A Cog may carry a model and the software that executes it, and installing such a
Cog makes that model available. That is the content the installer chose to
accept. No other authority follows from installation, and admitted content is
never admitted authority — a bundled runtime included.

The surrounding runtime or user remains responsible for granting and enforcing
authority. Implementations may define richer permission profiles or extensions,
but they must not imply that those profiles are part of CogSpec v0.1.

## Evaluation

A Cog may contain evaluation examples, fixtures, criteria, or results
in an `evaluation/` directory or another referenced location.

CogSpec v0.1 does not define an evaluation schema, universal metrics, passing
thresholds, or what evidence must accompany a release.

Authors should explain how they know the Cog is useful and where it is known to
fail. Implementations should not treat the presence of a CogSpec-compatible
file as evidence that the Cog is safe or effective.

## Validation

A v0.1 validator checks that:

1. the supplied Cog Markdown file is valid UTF-8;
2. it begins with valid YAML frontmatter, within the shape and syntax limits in
   [What belongs in the frontmatter](#what-belongs-in-the-frontmatter);
3. the frontmatter contains valid `type`, `name`, and `description` fields;
4. `name` follows the naming rules;
5. optional fields this specification defines are well-formed when present:
   `metadata` maps string keys to string values, and `kind` is one of `model`,
   `context`, or `complete`;
6. local file references do not use absolute paths or escape the Cog root; and
7. the Cog declares both `manifest` and `manifest_schema`; the path is relative,
   resolves to a file that exists inside the Cog root after symbolic links are
   followed, and the schema identifier is a non-empty string.

The validator does not open, parse, or interpret the manifest, because v0.1 does
not define its format or contents.

A validator given a loose Markdown file rather than a directory checks 1 through
5 and reports the subject as a **draft**: a well-formed Cog document that is not
yet a Cog.

A validator accepts a directory and looks for `COG.md` as its entry file. It may
also accept a loose Markdown file, which it reports as a draft.

Unknown frontmatter fields and additional bundle files must not, by themselves,
cause a core v0.1 validator to reject an otherwise conforming Cog. They may be
preserved or ignored. A profile-aware validator may validate them against that
profile. An implementation must not interpret an unknown field as granting
authority.

An unknown field is still bound by the shape and syntax limits in
[What belongs in the frontmatter](#what-belongs-in-the-frontmatter), key grammar
included. Being unnamed here buys a field freedom of meaning, not of form.

Validation establishes format compatibility only. It does not establish
quality, safety, authenticity, licensing rights, or runtime compatibility.

## Expected implementation handling

At minimum, an implementation supporting CogSpec v0.1 should be able to:

1. discover `COG.md` as the entry file of a Cog directory;
2. recognize `type: cog` and `type: cog [0.1]`;
3. read the required metadata;
4. locate the manifest named by `manifest`, and report that it was not
   interpreted when the implementation does not understand its format;
5. present or load the Markdown body as the Cog's human-readable work contract;
6. make referenced files available when supported;
7. keep authority decisions outside the Cog text; and
8. report unsupported references or declared requirements instead of silently
   pretending to satisfy them.

Implementations are not required to execute every Cog they can read.
Implementations are also not required to understand every extension profile in
order to recognize the core Cog definition.

## Minimal example

A draft: a `COG.md` written before its manifest exists. Adding `manifest:`,
`manifest_schema:`, and the file they name makes it a Cog; nothing below
changes.

```markdown
---
type: cog [0.1]
name: research-analyst
description: Researches a defined question and produces a concise, source-aware briefing.
---

# Research Analyst

Investigate the question supplied by the user and produce a concise briefing.

## Boundaries

- Distinguish sourced facts from analysis.
- State important uncertainty and missing information.
- Do not invent sources.
```

## More complete example

```markdown
---
type: cog [0.1]
name: repository-risk-analyst
description: Reviews dependency evidence for a repository snapshot and produces a prioritized risk brief for engineering leaders.
manifest: cog.yaml
manifest_schema: example.org/cog-package [0.1]
kind: context
version: "0.1.0"
publisher: Example Organization
license: Apache-2.0
metadata:
  category: software-risk
  maturity: experimental
---

# Repository Risk Analyst

## Purpose

Turn dependency manifests, software bills of materials, and available security
alerts into a short, prioritized risk brief.

## Supported work

- Review one repository snapshot at a time.
- Identify material dependency and maintenance risks.
- Cite the evidence used for each finding.
- Recommend investigation or remediation for human review.

## Unsupported work

- Do not modify repository contents.
- Do not dismiss alerts or approve dependencies.
- Do not make legal or compliance determinations.

## Inputs

- Repository identity and immutable revision.
- Available dependency evidence.
- The user's risk priorities and constraints.

## Output

Produce an executive summary, prioritized findings, evidence references,
recommended next steps, and important limitations.

## Working method

1. Review only the supplied or explicitly admitted evidence.
2. Separate observed facts from inference.
3. Prioritize findings using the user's stated criteria.
4. State uncertainty and missing evidence.
5. Refuse requests outside the supported work above.
```

## What v0.1 does not try to define

This version intentionally does not standardize:

- the contents of the manifest, including any capability, interface, or
  dependency vocabulary;
- canonical global Cog identity;
- immutable release packaging or content digests;
- signatures, provenance, or publisher verification;
- formal input and output schemas;
- model selection or model capability vocabularies;
- tool or capability taxonomies;
- machine-enforced permissions and approvals;
- context assembly or Frame resolution;
- Skill resolution;
- memory and retention;
- evaluation formats or evidence requirements;
- deployment, execution, or run records;
- execution-portability claims;
- orchestration or delegation;
- publication registries; or
- commercial terms.

These may be defined by implementations and extension profiles. They should
enter a future core only after use demonstrates a need for interoperable
behavior.

## Sharing

A Cog may be shared through Git, a file archive, or a package registry. A draft
— a `COG.md` with no manifest yet — may be shared as a single file through
email or chat. CogSpec v0.1 requires no special infrastructure for either.

Implementations and users should treat Cogs as untrusted instructions unless
they trust the source. Loading a Cog can influence model behavior even though it
does not grant external authority. Referenced files carry the same trust level
as the Cog body because an implementation may load them into the worker's
context.

## Relationship to future versions

This is the initial adopt-now specification and a concrete basis for
discussion. Future versions may add standardized packaging, identity,
capabilities, evaluation evidence, runtime profiles, or execution receipts.

Those features should not be added merely because they are imaginable. A
future boundary should normally be supported by multiple real Cogs, a concrete
interoperability or safety need, and implementation experience.

The existing exploratory implementations inform this draft but are not
independent proof that a boundary is portable.
