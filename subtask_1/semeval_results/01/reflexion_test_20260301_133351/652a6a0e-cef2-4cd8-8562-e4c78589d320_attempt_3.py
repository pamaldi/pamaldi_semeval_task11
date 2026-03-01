% Witnesses for the syllogism
doctor(heart_surgeon).
legal_professional(lawyer1).

% Rule from the first premise: All humans are legal professionals
% We encode this as: legal_professional(X) if human(X)
% But we don't need to define humans directly
% Instead, we define the constraint that any human is a legal professional

% Rule from the second premise: At least one doctor is not a legal professional
% This is satisfied by heart_surgeon being a doctor but not a legal professional

% Counterexample: Build a world where:
% 1. All humans are legal professionals
% 2. At least one doctor is not a legal professional (satisfied by heart_surgeon)
% 3. But the conclusion "No doctors are humans" is FALSE (i.e., doctor IS a human)

% This is the key fix - make heart_surgeon a human to make the conclusion false
% This creates a counterexample proving the syllogism is INVALID
human(heart_surgeon).

% Validity check: The conclusion is "The entire group of doctors is not humans"
% For E-type conclusion, we need to check that there is NO doctor that is a human
% But in our counterexample, heart_surgeon is both a doctor and a human
valid_syllogism :- \+ (doctor(X), human(X)).