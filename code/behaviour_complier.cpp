int a = 1 + 1;                  // well-defined: always 2

char c = 200;                   // implementation-defined:
                                 // signed/unsigned char depends on compiler,
                                 // but compiler must document it

int x = f1() + f2();            // unspecified: eval order of f1/f2
                                 // not fixed, no docs required

int y = INT_MAX; y = y + 1;     // UB: signed overflow, anything can happen

// Rule of thumb: the looser the guarantee, the more you must avoid
// writing portable code that *depends* on the exact behavior.
