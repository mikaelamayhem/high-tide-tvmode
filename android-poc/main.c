/* High Tide Android TV probe: does a libadwaita window show up on Android,
 * and do remote / controller presses reach GTK? Every key press is shown
 * in the window and logged with the prefix "HTPROBE". */

#include <adwaita.h>

static GtkLabel *last_key;

static gboolean
on_key (GtkEventControllerKey *ctl, guint keyval, guint keycode,
        GdkModifierType state, gpointer data)
{
  const char *name = gdk_keyval_name (keyval);
  g_autofree char *text = g_strdup_printf ("Last key: %s (keyval 0x%x, code %u)",
                                           name ? name : "?", keyval, keycode);
  gtk_label_set_text (last_key, text);
  g_message ("HTPROBE key %s", text);
  return GDK_EVENT_PROPAGATE;
}

static void
on_clicked (GtkButton *button, gpointer data)
{
  g_message ("HTPROBE clicked %s", gtk_button_get_label (button));
  gtk_label_set_text (last_key, g_strdup_printf ("Activated: %s",
                                                 gtk_button_get_label (button)));
}

static void
activate (GApplication *app)
{
  GtkWidget *win = adw_application_window_new (GTK_APPLICATION (app));
  GtkWidget *view = adw_toolbar_view_new ();
  GtkWidget *box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 18);
  GtkWidget *row = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  GtkWidget *title = gtk_label_new ("High Tide TV probe");
  const char *labels[] = { "Home", "Discover", "Queue", "Lyrics" };

  adw_toolbar_view_add_top_bar (ADW_TOOLBAR_VIEW (view), adw_header_bar_new ());
  gtk_widget_add_css_class (title, "title-1");
  gtk_widget_set_valign (box, GTK_ALIGN_CENTER);
  gtk_widget_set_halign (box, GTK_ALIGN_CENTER);
  gtk_widget_set_halign (row, GTK_ALIGN_CENTER);

  for (guint i = 0; i < G_N_ELEMENTS (labels); i++)
    {
      GtkWidget *b = gtk_button_new_with_label (labels[i]);
      gtk_widget_add_css_class (b, "pill");
      g_signal_connect (b, "clicked", G_CALLBACK (on_clicked), NULL);
      gtk_box_append (GTK_BOX (row), b);
    }

  last_key = GTK_LABEL (gtk_label_new ("Press a button on the remote or controller"));
  gtk_widget_add_css_class (GTK_WIDGET (last_key), "title-3");

  gtk_box_append (GTK_BOX (box), title);
  gtk_box_append (GTK_BOX (box), gtk_label_new (g_strdup_printf (
      "GTK %u.%u.%u, libadwaita %u.%u.%u",
      gtk_get_major_version (), gtk_get_minor_version (), gtk_get_micro_version (),
      adw_get_major_version (), adw_get_minor_version (), adw_get_micro_version ())));
  gtk_box_append (GTK_BOX (box), row);
  gtk_box_append (GTK_BOX (box), GTK_WIDGET (last_key));
  adw_toolbar_view_set_content (ADW_TOOLBAR_VIEW (view), box);
  adw_application_window_set_content (ADW_APPLICATION_WINDOW (win), view);

  GtkEventController *keys = gtk_event_controller_key_new ();
  gtk_event_controller_set_propagation_phase (keys, GTK_PHASE_CAPTURE);
  g_signal_connect (keys, "key-pressed", G_CALLBACK (on_key), NULL);
  gtk_widget_add_controller (win, keys);

  gtk_window_present (GTK_WINDOW (win));
  g_message ("HTPROBE window presented");
}

int
main (int argc, char **argv)
{
  g_autoptr (AdwApplication) app =
    adw_application_new ("io.github.mikaelamayhem.HighTideTvProbe", G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect (app, "activate", G_CALLBACK (activate), NULL);
  return g_application_run (G_APPLICATION (app), argc, argv);
}
