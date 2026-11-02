project('hightide-tv-probe', 'c', version: '0.2.0', meson_version: '>= 1.9')

# Stage 2: the probe app embeds Python (official CPython Android build) and
# runs probe.py through PyGObject. CI unpacks these before configuring:
#   python/<cpu>/prefix/   CPython Android package for each architecture
#   pygobject/             PyGObject source tree
#   typelibs/              GObject introspection typelibs
cpu = host_machine.cpu_family()
py_ver = '3.14'
py_prefix = meson.current_source_dir() / 'python' / cpu / 'prefix'
py_home = get_option('datadir') / 'python' / cpu
site_packages = py_home / 'lib' / 'python' + py_ver / 'site-packages'

python_dep = declare_dependency(
  include_directories: include_directories('python' / cpu / 'prefix' / 'include' / 'python' + py_ver),
  link_args: ['-L' + py_prefix / 'lib', '-lpython' + py_ver],
)

gtk = dependency('gtk4')
adw = dependency('libadwaita-1')
gi_dep = dependency('girepository-2.0')
ffi_dep = dependency('libffi', required: false)
if not ffi_dep.found()
  ffi_dep = subproject('libffi').get_variable('ffi_dep')
endif

executable('hightide-tv-probe', 'main.c',
  dependencies: [gtk, adw, python_dep],
  c_args: ['-DPROBE_CPU="' + cpu + '"', '-DPROBE_PY_VER="' + py_ver + '"'],
  android_exe_type: 'application',
  install: true,
  install_tag: 'runtime',
)

# CPython runtime: libpython and its helper libraries go to jniLibs,
# the standard library goes to assets (extracted to files/share at start).
install_data(
  run_command('sh', '-c', 'ls ' + py_prefix / 'lib' / 'lib*.so', check: true).stdout().strip().split('\n'),
  install_dir: get_option('libdir'),
  install_tag: 'runtime',
)
install_subdir('python' / cpu / 'prefix' / 'lib' / 'python' + py_ver,
  install_dir: py_home / 'lib',
  exclude_directories: ['test', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip'],
  install_tag: 'runtime',
)

# PyGObject, built from source against the Android Python and GLib.
pygobject_conf = configuration_data()
pygobject_ver = run_command('sh', '-c',
  'sed -n "s/^ *version *: *\'\\([0-9.]*\\)\'.*/\\1/p" pygobject/meson.build | head -1',
  check: true).stdout().strip()
pv = pygobject_ver.split('.')
pygobject_conf.set('PYGOBJECT_MAJOR_VERSION', pv[0])
pygobject_conf.set('PYGOBJECT_MINOR_VERSION', pv[1])
pygobject_conf.set('PYGOBJECT_MICRO_VERSION', pv[2])
configure_file(output: 'config.h', configuration: pygobject_conf)

gi_sources = run_command('sh', '-c', 'cd pygobject/gi && ls *.c | grep -v pygi-foreign-cairo.c',
  check: true).stdout().strip().split('\n')

gi_files = []
foreach f : gi_sources
  gi_files += 'pygobject/gi' / f
endforeach

shared_module('_gi', gi_files,
  dependencies: [python_dep, gtk, gi_dep, ffi_dep],
  include_directories: include_directories('.', 'pygobject', 'pygobject/gi', 'pythoncapi-compat'),
  c_args: ['-DPY_SSIZE_T_CLEAN', '-D_INSIDE_PYGOBJECT_', '-DHAVE_CONFIG_H', '-fno-strict-aliasing',
           '-Wno-incompatible-pointer-types', '-Wno-int-conversion'],
  name_prefix: '',
  name_suffix: 'so',
  install: true,
  install_dir: site_packages / 'gi',
  install_tag: 'runtime',
)
install_subdir('pygobject/gi',
  install_dir: site_packages,
  exclude_files: ['meson.build', 'overrides/meson.build', 'repository/meson.build'],
  install_tag: 'runtime',
)

install_data('probe.py', install_dir: get_option('datadir') / 'hightide-probe', install_tag: 'runtime')

# High Tide itself. CI stages app/ (high_tide package, gresource, pydeps).
install_data('launch.py', install_dir: get_option('datadir') / 'high-tide', install_tag: 'runtime')
install_subdir('app', install_dir: get_option('datadir') / 'high-tide',
  strip_directory: true, install_tag: 'runtime')
install_data('../data/io.github.nokse22.high-tide.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas', install_tag: 'runtime')
install_subdir('typelibs', install_dir: get_option('datadir') / 'girepository-1.0',
  strip_directory: true, install_tag: 'runtime')
