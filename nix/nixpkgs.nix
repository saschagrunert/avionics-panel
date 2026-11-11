# The nixpkgs every build uses: the revision locked in ../flake.lock (Dependabot moves it), as a path in the
# Nix store. build.sh (NIX_PATH) and the lint workflow (-I) make <nixpkgs> and nix-shell -p resolve to it, so
# neither needs the flakes feature.
let
  lock = (builtins.fromJSON (builtins.readFile ../flake.lock)).nodes.nixpkgs.locked;
in
builtins.fetchTarball {
  url = "https://github.com/${lock.owner}/${lock.repo}/archive/${lock.rev}.tar.gz";
  sha256 = lock.narHash;
}
