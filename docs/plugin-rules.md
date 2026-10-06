# Plugin rules: lifecycle and guidelines

A plugin ships an executable `rules` file (default: `wazo/rules`).
wazo-plugind calls it with one action as the first argument.
It also wraps the plugin in a generated `.deb` and generates the dpkg
maintainer scripts (`postinst`, `prerm`, `postrm`) that call the rules file.

## Actions

| Action      | Called by                             | A failure …                          |
|-------------|---------------------------------------|--------------------------------------|
| `build`     | wazo-plugind, when it builds          | fails the installation               |
| `package`   | wazo-plugind, when it builds          | fails the installation               |
| `install`   | `postinst configure`                  | fails the installation               |
| `uninstall` | `prerm remove`                        | is logged, removal goes on           |
| `postrm`    | `postrm remove`                       | is logged, removal goes on           |

`postrm` is called only when `plugin_format_version` is 1 or higher in
`plugin.yml`.

## What the generated package scripts guarantee

- The rules file is copied to `/var/lib/wazo-plugind/rules/rules.<name>.<namespace>`
  at `prerm remove`. The `postrm` action runs from this copy, because the
  package files are already gone when `postrm` runs.
- Removal always completes. Missing rules files and failing `uninstall` or
  `postrm` actions produce a warning on stderr, never a dpkg error.
- `postrm remove` runs the `postrm` action. `postrm purge` only deletes the
  copy of the rules file. A purge succeeds even if the copy is already gone,
  and also when the package was removed a long time before.
- Each maintainer script can be run again after an interruption.

wazo-plugind uninstalls plugins with `apt-get remove`, so a removed plugin stays
in the `rc` state in dpkg until someone runs `apt purge`.

## Guidelines for plugin authors

1. **Make every action idempotent.** dpkg can run an action again after an
   interruption. Use `mkdir -p`, `rm -f`, `ln -sf`, and test before you change.
2. **Accept missing state.** In `uninstall` and `postrm`, a file, a directory,
   a user or a service can be absent already. Do not fail because of it.
3. **Do not use exit codes to block removal.** Failures of `uninstall` and
   `postrm` do not stop the removal. Report the problem on stderr.
4. **Clean up in `postrm`, not in `uninstall`.** Use `uninstall` to stop what
   the plugin runs. Use `postrm` to delete what `install` created outside the
   package, for example generated files or configuration.
5. **In `postrm`, do not depend on the plugin files.** The rules file runs from
   a copy, and the package files are already removed. Use absolute paths and
   standard system tools only.
6. **Do not depend on other plugins in `uninstall` and `postrm`.** The package
   that you depend on can be removed first.
7. **Be non-interactive and independent of the working directory.** No
   prompts, no relative paths, no network access in removal actions.
8. **Handle every action you declare, and reject others.** End the script
   with a `*)` branch that prints a message and exits with a non-zero code.
9. **Test the full life cycle.** Install, uninstall (`apt-get remove`), purge
   (`apt-get purge`), then install again. Run `uninstall` and `postrm` twice.

## Packages built with an older wazo-plugind

Before this change, `postrm` called the copy of the rules file on both `remove`
and `purge`, and deleted it at `remove`. A later `purge` failed because the
file no longer existed. The package then stayed in the `rc` state.

To purge such a package, create an empty rules file at the path that the
`RULES=` line of `/var/lib/dpkg/info/<package>.postrm` shows, and purge again:

```sh
rules=/var/lib/wazo-plugind/rules/rules.<name>.<namespace>
printf '#!/bin/sh\nexit 0\n' > "$rules" && chmod 755 "$rules"
dpkg --purge wazo-plugind-<name>-<namespace>
```
