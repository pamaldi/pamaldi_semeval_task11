% Facts for the I-conclusion (some programs are not hardware) 
% This is the counterexample to test invalidity
program(wordprocessor).
software(wordprocessor).

% Fail clause for hardware since there are no hardware programs
hardware(_) :- fail.

% A-premise: All programs are software
software(X) :- program(X).

% E-premise: No software is hardware
conflict :- software(X), hardware(X).

% Validity check: Some programs are not hardware
valid_syllogism :- program(X), \+ hardware(X).