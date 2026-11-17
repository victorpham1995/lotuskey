{
  description = "LotusKey - Native Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      version = builtins.replaceStrings [ "\n" "\r" " " ] [ "" "" "" ] (builtins.readFile ./packaging/VERSION);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonEnv = pkgs.python3.withPackages (ps: [ ps.pygobject3 ]);
        in
        rec {
          ibus-lotuskey = pkgs.stdenv.mkDerivation {
            pname = "ibus-lotuskey";
            inherit version;
            src = self;

            nativeBuildInputs = with pkgs; [
              gcc
              pkg-config
              wrapGAppsHook3
              gobject-introspection
              autoPatchelfHook
            ];

            buildInputs = with pkgs; [
              glib
              ibus
              gtk3
              gdk-pixbuf
              librsvg
              libnotify
              pythonEnv
              stdenv.cc.cc.lib
            ];

            buildPhase = ''
              runHook preBuild
              bash packaging/build_binaries.sh
              runHook postBuild
            '';

            installPhase = ''
              runHook preInstall
              PREFIX="$out" ETCDIR="$out/etc" bash packaging/stage_install.sh "/" "$out/lib/udev/rules.d"
              sed -i "s|exec python3 |exec ${pythonEnv}/bin/python3 |g" \
                "$out/bin/lotuskey-setup" \
                "$out/bin/lotuskey-menu" \
                "$out/bin/lotuskey-wizard"
              sed -i "1s|^#!/usr/bin/env python3|#!${pythonEnv}/bin/python3|" \
                "$out/bin/lotuskey-autostart"
              runHook postInstall
            '';

            meta = with pkgs.lib; {
              description = "Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)";
              homepage = "https://github.com/victorpham1995/lotuskey";
              license = licenses.mit;
              platforms = [ "x86_64-linux" "aarch64-linux" ];
              mainProgram = "lotuskey-setup";
            };
          };

          default = ibus-lotuskey;
        }
      );

      overlays.default = final: prev: {
        ibus-lotuskey = self.packages.${prev.system}.ibus-lotuskey;
      };

      nixosModules.default = { config, lib, pkgs, ... }:
        let
          cfg = config.i18n.inputMethod.lotuskey;
          pkg = self.packages.${pkgs.system}.ibus-lotuskey;
        in
        {
          options.i18n.inputMethod.lotuskey = {
            enable = lib.mkEnableOption "LotusKey Vietnamese Input Method";
          };

          config = lib.mkIf cfg.enable {
            i18n.inputMethod = {
              enable = lib.mkDefault true;
              type = lib.mkDefault "ibus";
              ibus.engines = [ pkg ];
            };
            environment.systemPackages = [ pkg ];
            services.udev.packages = [ pkg ];
            boot.kernelModules = [ "uinput" ];
          };
        };
    };
}
