/* High Tide Android TV probe, stage 2.
 *
 * Starts the bundled CPython and runs probe.py, which builds the window
 * with PyGObject. If Python fails to start, a plain C window shows the
 * error instead. Log lines carry the prefix "HTPROBE". */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <adwaita.h>

static char *python_error;

static const char *
data_dir (void)
{
  /* The GTK Android runtime extracts the APK assets to files/share and
   * makes it the first system data dir. */
  return g_get_system_data_dirs ()[0];
}

static int
run_python (int argc, char **argv)
{
  g_autofree char *home = g_build_filename (data_dir (), "python", PROBE_CPU, NULL);
  g_autofree char *typelibs = g_build_filename (data_dir (), "girepository-1.0", NULL);
  g_autofree char *script = g_build_filename (data_dir (), "hightide-probe", "probe.py", NULL);
  PyConfig config;
  PyStatus status;
  FILE *fp;
  int rc;

  g_setenv ("GI_TYPELIB_PATH", typelibs, TRUE);
  g_message ("HTPROBE python home %s, typelibs %s", home, typelibs);

  PyConfig_InitIsolatedConfig (&config);
  config.install_signal_handlers = 0;
  status = PyConfig_SetBytesString (&config, &config.home, home);
  if (!PyStatus_Exception (status))
    status = PyConfig_SetBytesArgv (&config, argc, argv);
  if (!PyStatus_Exception (status))
    status = Py_InitializeFromConfig (&config);
  PyConfig_Clear (&config);
  if (PyStatus_Exception (status))
    {
      python_error = g_strdup_printf ("Python failed to start: %s",
                                      status.err_msg ? status.err_msg : "unknown error");
      g_warning ("HTPROBE %s", python_error);
      return -1;
    }

  g_message ("HTPROBE python started: %s", Py_GetVersion ());

  fp = fopen (script, "r");
  if (!fp)
    {
      python_error = g_strdup_printf ("Could not open %s", script);
      g_warning ("HTPROBE %s", python_error);
      return -1;
    }
  rc = PyRun_SimpleFileEx (fp, script, 1);
  if (rc != 0)
    python_error = g_strdup ("probe.py raised an exception, see logcat (tag python.stderr)");
  return rc;
}

static void
activate_fallback (GApplication *app)
{
  GtkWidget *win = adw_application_window_new (GTK_APPLICATION (app));
  GtkWidget *page = adw_status_page_new ();

  adw_status_page_set_title (ADW_STATUS_PAGE (page), "Python did not start");
  adw_status_page_set_description (ADW_STATUS_PAGE (page), python_error);
  adw_application_window_set_content (ADW_APPLICATION_WINDOW (win), page);
  gtk_window_present (GTK_WINDOW (win));
}

int
main (int argc, char **argv)
{
  if (run_python (argc, argv) == 0 && !python_error)
    return 0;

  g_autoptr (AdwApplication) app =
    adw_application_new ("io.github.mikaelamayhem.HighTideTvProbe", G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect (app, "activate", G_CALLBACK (activate_fallback), NULL);
  return g_application_run (G_APPLICATION (app), argc, argv);
}
