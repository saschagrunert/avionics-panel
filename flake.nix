{
  # Only pins nixpkgs: flake.lock holds the revision, which Dependabot moves along nixpkgs-unstable.
  # build.sh and the lint workflow read the lock through nix/nixpkgs.nix, without flakes.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs = _: { };
}
