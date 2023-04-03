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
        inherit (poetry2nix.legacyPackages.${system}) mkPoetryEnv;
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;

        poetryCommon = {
          inherit python;
          projectDir = self;
          preferWheels = true;
          groups = [ "dev" "docs" "jupyter" ];
          editablePackageSources = {
            quantpiler = ./quantpiler;
          };
        };
        poetryEnv = mkPoetryEnv poetryCommon;
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
