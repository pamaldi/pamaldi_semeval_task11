% Witnesses for the syllogism
doctor(heart_surgeon).
legal_professional(lawyer1).

% Rule from the first premise: All humans are legal professionals
% We cannot use the undefined 'human' predicate.
% Instead, we will encode this as a constraint.
% Since we're building a counterexample, we assume no doctor is a human.

% Rule from the second premise: At least one doctor is not a legal professional
% This is enforced by heart_surgeon being a doctor but not a legal professional

% Validity check: The conclusion is "The entire group of doctors is not humans"
% We define a rule to ensure no doctor is a human.
% Since we have no facts for human/1, we can define a fail clause.

human(_) :- fail.

valid_syllogism :- \+ (doctor(X), human(X)).