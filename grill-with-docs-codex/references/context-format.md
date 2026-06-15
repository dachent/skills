# CONTEXT.md Format

## Structure

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**Order**:
{A one or two sentence description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

## Rules

- Be opinionated. When multiple words exist for the same concept, pick the best one and list the others under `_Avoid_`.
- Keep definitions tight. One or two sentences max. Define what it is, not what it does.
- Only include terms specific to this project's context.
- General programming concepts, utility patterns, and implementation details do not belong.
- Before adding a term, ask whether it is a domain concept unique to this context.
- Group terms under subheadings when natural clusters emerge. If all terms belong to one cohesive area, a flat list is fine.

## Single vs Multi-Context Repositories

Single context repositories usually have one `CONTEXT.md` at the repo root.

Multiple context repositories use a root `CONTEXT-MAP.md`:

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md) - receives and tracks customer orders
- [Billing](./src/billing/CONTEXT.md) - generates invoices and processes payments
- [Fulfillment](./src/fulfillment/CONTEXT.md) - manages warehouse picking and shipping

## Relationships

- **Ordering -> Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to start picking
- **Fulfillment -> Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them to generate invoices
- **Ordering <-> Billing**: Shared types for `CustomerId` and `Money`
```

Infer the structure:

- If `CONTEXT-MAP.md` exists, read it to find contexts.
- If only a root `CONTEXT.md` exists, treat the repo as single-context.
- If neither exists, create a root `CONTEXT.md` lazily when the first term is resolved.
- When multiple contexts exist, infer which context the topic relates to. If unclear, ask.
