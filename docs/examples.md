# Examples

## Basic Local Design Generation

```bash
desysflow design --source . --out ./desysflow --project ecommerce-system
```

## Focused Refinement

```bash
desysflow redesign \
  --source . \
  --out ./desysflow \
  --project ecommerce-system \
  --focus "optimize checkout scalability and caching"
```

## Resume a Previous Session

```bash
desysflow resume <session_id> --source . --out ./desysflow --project ecommerce-system
```

## Show Local History

```bash
desysflow history --out ./desysflow
```

## Run API + UI Together

```bash
./letsvibedesign dev
```

## Generate with Explicit Options

```bash
desysflow design \
  --source . \
  --out ./desysflow \
  --project ecommerce-system \
  --language python \
  --cloud aws \
  --style detailed \
  --web-search auto
```
