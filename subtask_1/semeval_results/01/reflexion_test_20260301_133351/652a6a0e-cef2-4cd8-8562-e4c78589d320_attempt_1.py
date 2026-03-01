% Witnesses for the counterexample
legal_professional(lawyer1).
doctor(heart_surgeon).

% Rule from the first premise: All humans are legal professionals
legal_professional(X) :- human(X).

% Rule from the second premise: Some doctor is not a legal professional
% This is enforced by ensuring heart_surgeon is a doctor but not a legal professional

% Rule from the third premise: No doctor is a human
% This is enforced by ensuring heart_surgeon is not a human

% Validity check: The conclusion is "The entire group of doctors is not humans"
valid_syllogism :- \+ (doctor(X), human(X)).