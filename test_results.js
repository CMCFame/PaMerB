module.exports = [
    {
        label: "Live Answer",
        maxLoop: [
            "Main",
            3,
            "Problems"
        ],
        playLog: [
            "Welcome",
            "This is an electric callout from",
            "Level location spoken"
        ],
        playPrompt: [
            "callflow:ENV_VAR",
            "callflow:1614",
            "location:{{level1_location}}"
        ],
    },
    {
        log: "environment",
        guard: "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
        playPrompt: "callflow:{{env}}",
        nobarge: 1,
    },
    {
        playLog: [
            "Press 1 if this is",
            "Employee name spoken({{contact_id}})",
            "Employee name spoken",
            "to the phone",
            "Employee name spoken",
            "is not home",
            "Press 9, to repeat this message",
            "9 - repeat, or invalid input"
        ],
        playPrompt: [
            "callflow:1002",
            "names:{{contact_id}}",
            "names:{{contact_id}}",
            "callflow:1006",
            "names:{{contact_id}}",
            "callflow:1004",
            "callflow:1643",
            "callflow:1009"
        ],
        getDigits: {
            numDigits: 1,
            maxTime: 1,
            validChoices: "1|3|7|9",
            errorPrompt: "callflow:1009"
        },
        branch: {
            1: "Employee",
            error: "Second Message",
            7: "Have",
            3: "Second Message",
            9: "Live Answer"
        },
    },
    {
        label: "Employee",
        log: "1 - this is employee",
        playPrompt: [
            "callflow:1002"
        ],
        playLog: [
            "1 - this is employee"
        ],
    },
    {
        label: "Invalid Entry",
        log: "Invalid Entry Invalid entry. Please try again.",
        playPrompt: [
            "callflow:1009",
            "callflow:1009",
            "callflow:1017"
        ],
        playLog: [
            "Invalid Entry",
            "Invalid entry",
            "Please try again"
        ],
        branch: {
            error: "Live Answer",
            none: "Problems"
        },
        maxLoop: [
            "Loop-Invalid Entry",
            5,
            "Problems"
        ],
        getDigits: {
            errorPrompt: "callflow:1009",
            nonePrompt: "callflow:1009"
        },
        nobarge: 1,
    },
    {
        label: "Enter",
        log: "Enter Employee PIN Please enter your 4 digit PIN followed by the pound key.",
        playPrompt: [
            "callflow:1097",
            "callflow:1008",
            "callflow:1008"
        ],
        playLog: [
            "Enter Employee PIN",
            "Please enter your 4 digit PIN",
            "followed by the pound key"
        ],
        getDigits: {
            numDigits: 5,
            maxTries: 3,
            maxTime: 7,
            validChoices: "{{pin}}",
            errorPrompt: "callflow:1009",
            nonePrompt: "callflow:1009"
        },
        branch: {
            1: "Enter PIN",
            next: "After PIN"
        },
        branchOn: "{{pin_req}}",
    },
    {
        label: "\"Correct Pin",
        log: "Correct PIN?",
        playPrompt: [
            "callflow:1139"
        ],
        playLog: [
            "Correct PIN"
        ],
        branch: {
            no: "Invalid Entry",
            yes: "Electric Callout",
            error: "Problems",
            none: "Problems"
        },
    },
    {
        label: "Electric Callout",
        log: "Electric Callout This is an electric callout.",
        playPrompt: [
            "callflow:1274",
            "callflow:1614"
        ],
        playLog: [
            "Electric Callout",
            "This is an electric callout"
        ],
        goto: "Callout Reason",
        maxLoop: [
            "Main",
            3,
            "Problems"
        ],
    },
    {
        label: "Callout Reason",
        log: "Callout Reason The callout reason is (callout reason).",
        playPrompt: [
            "callflow:1019",
            "callflow:1019",
            "reason:{{callout_reason}}"
        ],
        playLog: [
            "Callout Reason",
            "The callout reason is",
            "Callout reason spoken"
        ],
        goto: "Trouble Location",
        guardPrompt: "reason:{{callout_reason}}",
    },
    {
        label: "Trouble Location",
        log: "Trouble Location The trouble location is (trouble location).",
        playPrompt: [
            "callflow:1232",
            "callflow:1232",
            "location:{{callout_location}}"
        ],
        playLog: [
            "Trouble Location",
            "The trouble location is",
            "Trouble location spoken"
        ],
        goto: "Custom Message",
        guardPrompt: "location:{{callout_location}}",
    },
    {
        label: "Custom Message",
        log: "Custom Message (Play custom message, if selected.)",
        playPrompt: [
            "callflow:1643",
            "callflow:1002"
        ],
        playLog: [
            "Custom Message",
            "(Play custom message, if selected"
        ],
        goto: "\"Available For Callout",
        nobarge: 1,
        guardPrompt: "custom:{{custom_message}}",
    },
    {
        label: "\"Available For Callout",
        log: "Available For Callout Are you available to work this callout? If yes, press 1.",
        playPrompt: [
            "callflow:1274",
            "callflow:1297",
            "callflow:PRS1NEU",
            "callflow:PRS3NEU",
            "[VOICE FILE NEEDED]"
        ],
        playLog: [
            "Available For Callout",
            "Are you available to work this callout",
            "If yes, press 1",
            "If no, press 3",
            "If no one else accepts, and you want to be called again, press 9"
        ],
        branch: {
            error: "Invalid Entry",
            none: "Invalid Entry",
            1: "Confirm Accept"
        },
        maxLoop: [
            "Main",
            3,
            "Problems"
        ],
    },
    {
        label: "Confirm Accept",
        log: "You pressed 1 to accept. Please press 1 again to confirm",
        playPrompt: [
            "callflow:1366"
        ],
        playLog: [
            "You pressed 1 to accept. Please press 1 again to confirm"
        ],
        getDigits: {
            numDigits: 1,
            maxTries: 1,
            maxTime: 7,
            validChoices: "1"
        },
        branch: {
            1: "Accept",
            error: "Invalid_Response",
            none: "Invalid_Response"
        },
    },
    {
        label: "Invalid_Response",
        log: "Invalid entry. Please try again",
        playPrompt: [
            "callflow:1009"
        ],
        playLog: [
            "Invalid entry. Please try again"
        ],
        maxLoop: [
            "Loop-D",
            3,
            "Problems"
        ],
        goto: "Offer",
        nobarge: 1,
    },
    {
        label: "Accept",
        log: "Accepted Response An accepted response has been recorded.",
        playPrompt: [
            "callflow:1297",
            "callflow:1297",
            "callflow:1104"
        ],
        playLog: [
            "Accepted Response",
            "An accepted response has",
            "been recorded"
        ],
        goto: "Goodbye Thank",
        gosub: ["SaveCallResult", 1001, "Accept"],
    },
    {
        label: "Goodbye Thank",
        log: "Goodbye Thank you. Goodbye.",
        playPrompt: [
            "[VOICE FILE NEEDED]",
            "callflow:1297",
            "[VOICE FILE NEEDED]"
        ],
        playLog: [
            "Goodbye",
            "Thank you",
            "Goodbye"
        ],
        goto: "hangup",
    },
    {
        label: "Hangup",
        log: "Disconnect",
        playPrompt: [
            "callflow:ENV_VAR"
        ],
        playLog: [
            "Disconnect"
        ],
        goto: "hangup",
    },
    {
        label: "Callout Decline",
        log: "Callout Decline Your response is being recorded as a decline.",
        playPrompt: [
            "callflow:1274",
            "callflow:1100"
        ],
        playLog: [
            "Callout Decline",
            "Your response is being recorded as a decline"
        ],
        goto: "Goodbye Thank",
        gosub: ["SaveCallResult", 1002, "Decline"],
    },
    {
        label: "Qualified You",
        log: "Qualified No You may be called again on this callout if no one accepts.",
        playPrompt: [
            "callflow:1145",
            "callflow:1297",
            "callflow:1019"
        ],
        playLog: [
            "Qualified No",
            "You may be called again on this",
            "callout if no one accepts"
        ],
        goto: "Goodbye Thank",
    },
    {
        label: "Confirm QualNo",
        log: "You pressed 7 to be called again. Please press 7 again to confirm",
        playPrompt: [
            "callflow:2136"
        ],
        playLog: [
            "You pressed 7 to be called again. Please press 7 again to confirm"
        ],
        getDigits: {
            numDigits: 1,
            maxTries: 1,
            maxTime: 7,
            validChoices: "7"
        },
        branch: {
            7: "QualNo",
            error: "Invalid_Response",
            none: "Invalid_Response"
        },
    },
    {
        label: "Invalid_Response",
        log: "Invalid entry. Please try again",
        playPrompt: [
            "callflow:1009"
        ],
        playLog: [
            "Invalid entry. Please try again"
        ],
        maxLoop: [
            "Loop-D",
            3,
            "Problems"
        ],
        goto: "Offer",
        nobarge: 1,
    },
    {
        label: "Second Message",
        log: "30-second message Press any key to continue",
        playPrompt: [
            "callflow:1643",
            "callflow:1002",
            "callflow:1002"
        ],
        playLog: [
            "30-second message",
            "Press any key to",
            "continue"
        ],
        goto: "hangup",
        nobarge: 1,
    },
    {
        label: "Have",
        log: "Employee Not Home Please have (employee) call the (Level 2) Callout System at 8",
        playPrompt: [
            "callflow:1004",
            "callflow:1017",
            "callflow:1174",
            "callflow:1274",
            "callflow:1290",
            "[VOICE FILE NEEDED]"
        ],
        playLog: [
            "Employee Not Home",
            "Please have",
            "(employee) call the",
            "(Level 2) Callout",
            "System at",
            "866-502-7267"
        ],
        goto: "hangup",
    }
];
