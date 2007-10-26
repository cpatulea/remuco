package remuco.util;

import javax.microedition.lcdui.Form;


/**
 * A {@link remuco.util.ILogPrinter} implementation which prints out log
 * messages to a {@link Form}. This is useful for inspecting what happens
 * on a mobile device where STDOUT cannot be inspected.
 * 
 * @author Christian Buennig
 * 
 */
public final class FormLogger implements ILogPrinter {

    private final Form f;

    public FormLogger(Form f) {
        this.f = f;
    }

    private static int MAX_LOG_ELEMENTS = 70;

    public void print(String s) {
        checkFormSize();
        f.append(s);
    }

    public void println(String s) {
        checkFormSize();
        f.append(s + "\n");
    }

    public void println() {
        checkFormSize();
        f.append("\n");
    }

    private void checkFormSize() {
        if (f.size() >= MAX_LOG_ELEMENTS) {
            for (int i = 0; i < 10; i++) {
                f.delete(0);
            }
        }
    }

}