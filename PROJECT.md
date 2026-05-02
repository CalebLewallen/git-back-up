# Git Back Up

The Git Back Up project is an open source project meant to help developers and organizations create automatic backups to their code by mirroring their git repos using the git mirror capabilities.

The motivation for this project is due to the unreliable nature of Github in recent months as a forge. Developers should be able to ensure that their data is backed up to another hosted or self hosted service.

## Product Positioning

The primary use case for this is to automate periodic mirroring of git data from a source repository to a target repository. Users should be able to choose between only backing up select project history, like a main branch and a few select feature branches, or the entire project history.

Users should also have control over how they want to push changes. By default, a safe push should be made, with the user notified if changes cannot be safely merged/mirrored. Users should be able to override and force push changes if needed.

This isn't a code change management tool -- it's simply a way to help automate backups between two source control systems.

I expect users to be able to provide api keys for both services and push changes on demand.