# nix/packages.nix — Hermes Agent package built with uv2nix
{ inputs, ... }:
{
  perSystem =
    {
      pkgs,
      lib,
      inputs',
      ...
    }:
    let

      sandbox = pkgs.callPackage ./sandbox.nix { };

      minimal = pkgs.callPackage ./hermes-agent.nix {
        inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
        # Only embed clean revs — dirtyRev doesn't represent any upstream
        # commit, so comparing it would always claim "update available".
        rev = inputs.self.rev or null;
      };

      # Default platform-portable optional integrations. Modal is exposed as a
      # separate package below because its ARMv7 cbor2 pin conflicts with Vercel.
      full = minimal.override {
        extraDependencyGroups = [
          "anthropic"
          "azure-identity"
          "bedrock"
          "daytona"
          "dingtalk"
          "edge-tts"
          "exa"
          "fal"
          "feishu"
          "firecrawl"
          "hindsight"
          "honcho"
          "messaging"
          "parallel-web"
          "tts-premium"
          "vercel"
          "voice"
        ]
        # matrix is Linux-only (oqs/liboqs lacks aarch64-darwin wheels).
        ++ lib.optionals pkgs.stdenv.isLinux [ "matrix" ];
      };
    in
    {
      packages = {
        node-gyp =
          (pkgs.callPackage ./lib.nix {
            inherit (pkgs) npm-lockfile-fix;
          }).node-gyp;
        default = full;

        inherit sandbox;

        inherit minimal;

        # Modal and Vercel have mutually exclusive cbor2 requirements in the
        # universal lock. The default/full package keeps Vercel; expose Modal
        # as a separate sealed variant rather than selecting both branches.
        modal = minimal.override {
          extraDependencyGroups = [ "modal" ];
        };

        # Ships discord.py + python-telegram-bot + slack-sdk so a plain
        # `nix profile install .#messaging` connects to Discord/Telegram/Slack
        # on first run — lazy-install can't write to the read-only /nix/store.
        messaging = minimal.override {
          extraDependencyGroups = [ "messaging" ];
        };

        tui = full.hermesTui;
        web = full.hermesWeb;
        desktop = full.hermesDesktop;

        update-npm-lockfile = full.hermesNpmLib.updateNpmLockfile;
      };
    };
}
