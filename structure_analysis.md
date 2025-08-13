# allflows LITE Structure Analysis vs Current Output

## Key Differences Identified

### 1. **Property Names Format**
**Expected (from allflows LITE):**
```javascript
{
    numDigits: 1,           // NO quotes around property names
    maxTime: 1,
    validChoices: "1|3|7|9",
    errorPrompt: "callflow:1009"
}
```

**Current Output:**
```javascript
{
    "numDigits": 1,         // INCORRECT: quotes around property names
    "maxTime": 7,
    "validChoices": "1|2|3",
    "errorPrompt": "callflow:1009"
}
```

### 2. **Branch Structure**
**Expected:**
```javascript
branch: {
    1: "Enter PIN",         // Numbers as unquoted property names
    3: "Sleep",
    7: "Not Home", 
    9: "Live Answer",
    error: "Live Answer"
}
```

**Current Output:**
```javascript
branch: {
    "error": "Invalid Entry",    // INCORRECT: quotes around numbers
    "none": "Problems",
    "1": "Accepted Response"     // Should be: 1: "Accepted Response"
}
```

### 3. **playLog vs playPrompt Structure**
**Expected (separate arrays):**
```javascript
playLog: [
    "This is a",
    "L2 location", 
    "callout"
],
playPrompt: [
    "callflow:1210",
    "location:{{level2_location}}",
    "callflow:1274"
]
```

**Current Output:**
```javascript
playPrompt: [
    "callflow:1177",    // Wrong voice files
    "company:1202",     // Generic instead of specific
    "callflow:1178"
]
```

### 4. **Log Property Format**
**Expected:**
```javascript
log: "Dev Date: 2023-10-21 17:14:57"  // Clean, no truncation
```

**Current Output:**
```javascript
log: ""Welcome This is an electric callout from (Level 2). Press 1, if this is (employ..."  // ISSUES: double quotes, truncated
```

### 5. **maxLoop Structure**
**Expected:**
```javascript
maxLoop: [ "Main", 3, "Problems" ]
```

**Current Output:**
```javascript
// Missing from most nodes that should have it
```

### 6. **gosub Structure**
**Expected:**
```javascript
gosub: ["SaveCallResult", 1001, "Accept"]  // Simple array format
```

**Current Output:**
```javascript
gosub: [
    "SaveCallResult",
    [                           // INCORRECT: nested array
        1001,
        "Accept"
    ]
]
```

## Critical Issues in Current Welcome Node

### Expected Welcome Node Structure:
```javascript
{
    label: "Live Answer",
    maxLoop: [ "Main", 3, "Problems" ],
    playLog: [ "This is a", "L2 location", "callout" ],
    playPrompt: [ "callflow:1210", "location:{{level2_location}}", "callflow:1274" ]
},
{
    playLog: [
        "Press 1 if this is",
        "Employee name spoken({{contact_id}})",
        // ... more entries
    ],
    playPrompt: [
        "callflow:1002",
        "names:{{contact_id}}",
        // ... more entries  
    ],
    getDigits: {
        numDigits: 1,              // NO quotes
        maxTime: 1,
        validChoices: "1|3|7|9",
        errorPrompt: "callflow:1009"
    },
    branch: {
        1: "Enter PIN",            // NO quotes around numbers
        3: "Sleep",
        7: "Not Home",
        9: "Live Answer",
        error: "Live Answer"
    }
}
```

### Current Welcome Node Issues:
1. **Wrong Label**: "Invalid Input" instead of "Welcome" or "Live Answer"
2. **Missing DTMF Options**: Only has "3", missing 1, 7, 9
3. **Property Quote Issues**: All property names quoted
4. **Wrong Voice Files**: Using generic callout files instead of specific ones
5. **No maxLoop**: Missing retry logic
6. **Log Truncation**: Log text cut off with "..."

## Action Items

### High Priority Fixes:
1. **Remove quotes from object property names** in JavaScript output
2. **Fix branch mapping** to include all DTMF choices (1,3,7,9)
3. **Correct node labeling** to avoid truncation and quote issues
4. **Add maxLoop** to appropriate nodes
5. **Fix gosub structure** to simple array format
6. **Improve welcome node detection** to properly identify start node

### Medium Priority:
1. **Optimize voice file selection** for better content matching
2. **Improve playLog accuracy** with proper text segmentation
3. **Add missing nonePrompt** to getDigits structures

## Expected vs Actual Comparison

| Aspect | Expected | Current | Status |
|--------|----------|---------|---------|
| Property quotes | No quotes | Quoted | ❌ |
| Branch numbers | Unquoted | Quoted | ❌ |
| DTMF choices | 1,3,7,9 | Only 3 | ❌ |
| gosub format | Simple array | Nested | ❌ |
| maxLoop | Present | Missing | ❌ |
| Log format | Clean | Truncated | ❌ |
| playLog arrays | Accurate | Generic | ❌ |