# Shares

Persistent file-systems are provided by both volumes and
shares. Volumes are block devices inside the virtual machine, yielding
fast performance but mounted file-systems require exclusive
access. Shares allow mounting an arbitrary directory tree from the
host.

In `microvm.shares` elements the `proto` field allows either of two
values:

- `9p` (default) is built into many hypervisors, allowing you to
  quickly share a directory tree. Not supported by vfkit on macOS.

- `virtiofs` requires a separate virtiofsd service which is started as
  a prerequisite when you start MicroVMs through a systemd service
  that comes with the `microvm.nixosModules.host` module.

  If you want to run from the command-line, start `bin/virtiofsd-run`
  separately.

  Expect `virtiofs` to yield better performance over `9p`.

  **Note:** vfkit (macOS) has built-in virtiofs support and does not
  require a separate virtiofsd service.

```nix
microvm.shares = [ {
  proto = "virtiofs";
  tag = "home";
  # Source path can be absolute or relative
  # to /var/lib/microvms/$hostName
  source = "home";
  mountPoint = "/home";
} ];
```

<div class="warning">
When sharing a path that is on ZFS with virtiofs, the dataset must
have options
<code>-o xattr=sa -o acltype=posixacl</code>
</div>


## Per-share virtiofsd options

Each `virtiofs` share also supports:

- **`posixAcl`** (bool, default `true`): pass `--posix-acl --xattr`.
  Set to `false` to use `--translate-uid`/`--translate-gid`.
- **`extraArgs`** (list of strings, default `[]`): extra virtiofsd
  arguments for this share, appended after the global
  `microvm.virtiofsd.extraArgs`.

Example: map guest uid 999 to host uid 1000 for a single share:

```nix
microvm.shares = [ {
  proto = "virtiofs";
  tag = "hermes-prompts";
  source = "/var/lib/vibe-nix/hermes";
  mountPoint = "/run/hermes/prompts";
  posixAcl = false;
  extraArgs = [
    "--translate-uid" "guest:999:1000:1"
    "--translate-gid" "guest:999:1000:1"
  ];
} ];
```

`--translate-uid guest:GUEST_UID:HOST_UID:COUNT` remaps
`[GUEST_UID, GUEST_UID+COUNT)` in the guest to
`[HOST_UID, HOST_UID+COUNT)` on the host.


## DAX

DAX lets the guest map file contents directly from the host's page
cache instead of copying them through the virtqueue on every access,
which can noticeably improve performance for frequently accessed
files. See the [virtio-fs design
doc](https://virtio-fs.gitlab.io/design.html) for how the DAX window
works, and the [kernel DAX
docs](https://www.kernel.org/doc/html/latest/filesystems/dax.html)
for what DAX means on the guest's side of the mount. It is opt-in per
share:

- **`dax`** (bool, default `false`): enable DAX for this `virtiofs`
  share.
- **`daxWindowSize`** (string, default `"8G"`): size of the DAX
  shared-memory window, e.g. `"4G"`. Only used by cloud-hypervisor
  (passed as `cache_size`); the default matches both
  cloud-hypervisor's own built-in default and crosvm's hard-coded
  window size. Set to `null` to omit it on cloud-hypervisor and fall
  back to its own default instead.

Support is hypervisor-specific:

- **cloud-hypervisor** negotiates DAX with the externally spawned
  virtiofsd, same as any other `virtiofs` share.
- **crosvm** has no DAX support over the vhost-user frontend used for
  ordinary virtiofs shares. A `dax = true` share is instead served by
  crosvm's own built-in virtio-fs device, bypassing virtiofsd
  entirely. Read-only DAX shares are not supported on crosvm, since
  that built-in device has no read-only mode. The DAX window is a
  fixed 8GiB, hard-coded in crosvm; `daxWindowSize` has no effect
  here.
- **qemu** does not support DAX: QEMU removed the `cache-size` device
  property that used to expose a DAX window for `vhost-user-fs-pci`.

```nix
microvm.shares = [ {
  proto = "virtiofs";
  tag = "assets";
  source = "/var/lib/microvms/example/assets";
  mountPoint = "/assets";
  dax = true;
} ];
```

## Sharing a host's `/nix/store`

If a share with `source = "/nix/store"` is defined, size and build
time of the stage1 squashfs for `/dev/vda` will be reduced
drastically.

```nix
microvm.shares = [ {
  tag = "ro-store";
  source = "/nix/store";
  mountPoint = "/nix/.ro-store";
} ];
```

## Writable `/nix/store` overlay

An optional writable layer will be mounted if the path
`microvm.writableStoreOverlay` is set. Make sure that the path is
located on a writable filesystem.

**Caveat:** The Linux overlay filesystem is very picky about the
filesystems that can be the upper (writable) layer. 9p/virtiofs shares
don't work currently, so resort to using a volume for that:

```
{ config, ... }:
{
  microvm.writableStoreOverlay = "/nix/.rw-store";

  microvm.volumes = [ {
    image = "nix-store-overlay.img";
    mountPoint = config.microvm.writableStoreOverlay;
    size = 2048;
  } ];
}
```

<div class="warning">
The Nix database will forget all built packages after a
reboot, containing only what is needed for the VM's NixOS
system. Until this has been solved, it is recommended to just delete
and recreate the overlay after MicroVM shutdown or before startup.
</div>
