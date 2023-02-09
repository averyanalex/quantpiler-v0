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
        python = pkgs.python310;

        poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          preferWheels = true;
          python = python;
          groups = [ "dev" "docs" "jupyter" ];
          editablePackageSources = {
            quantpiler = ./quantpiler;
          };
        };
      in
      {
        devShells.default = poetryEnv.env.overrideAttrs (oldAttrs: {
          buildInputs = with pkgs; [
            pandoc
            poetry
          ];
        });
      }));
}
