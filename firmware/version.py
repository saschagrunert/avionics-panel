# version.py - the commit these files are from, its date and short hash, which code.py prints at startup.
# git archive fills it in (.gitattributes: export-subst), as for GitHub's Download ZIP and a release's source
# code, and so does windows/make_zip.py for the simulator's zip. A git checkout keeps the placeholder: code.py
# then prints "version unknown", and git log names the commit.
VERSION = "$Format:%cs, %h$"
