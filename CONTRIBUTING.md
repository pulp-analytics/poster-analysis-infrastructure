# Contributing

Thanks for your interest in contributing.

## Before you run anything against AWS

This repo exists partly because of a real four-figure billing incident
(see [docs/COST_SAFETY.md](docs/COST_SAFETY.md)). Before launching any
cost-bearing resource — EC2, Fargate, Batch, Bedrock, Rekognition,
Comprehend — run the pre-flight account check first:

```bash
AWS_PROFILE=<profile> PERSONAL_ACCOUNT_ID=<your account id> bash scripts/preflight_check.sh
```

Confirm it reports the account you expect before continuing.

## How to contribute

1. Fork the repo and create your branch from `main`.
2. Make your changes, with a clear commit message.
3. Open a pull request describing what changed and why.
4. Link any related issue.

## Reporting issues

Use the Issues tab. Include steps to reproduce, expected vs. actual behavior,
and relevant environment details (OS, Python version, etc.) when applicable.

## Code style

Keep changes focused and readable. Match the existing style in the file
you're editing rather than introducing a new one.

## License

By contributing, you agree that your contributions will be licensed under
the project's MIT License.
