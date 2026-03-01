% Facts for C++
cpp(cplusplus11).

% Facts for English
english(shakespeare).

% Rules from "All C++ is a programming language"
programming_language(X) :- cpp(X).

% Fail clause for English to enforce "No English is a programming language"
programming_language(_) :- fail.

% Validity check for "No English is C++"
valid_syllogism :- \+ (english(X), cpp(X)).