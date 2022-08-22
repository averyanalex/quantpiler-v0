{
  description = "Quantum compiler and common circuits library";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ poetry2nix.overlay ];
        };

        poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          preferWheels = true;
          python = pkgs.python310;
          editablePackageSources = {
            quantpiler = ./quantpiler;
          };
        };
      in
      {
        devShells.default = poetryEnv.env.overrideAttrs (oldAttrs: {
          buildInputs = with pkgs; [
            python310Packages.poetry
          ];
        });
      }));
}
