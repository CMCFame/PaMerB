# Enhanced PDF Processing & Multi-Callout Support Guide

## 🎯 **What's New**

Your PaMerB application now has **intelligent PDF processing** that can:
- ✅ **Skip title pages and non-diagram pages automatically**
- ✅ **Handle multi-page PDFs with different callout types**
- ✅ **Auto-detect callout types from content**
- ✅ **Process 13+ pages efficiently with smart filtering**

## 📋 **How to Use the Enhanced System**

### **1. Callout Configuration (Top Section)**

The callout configuration section at the top is your **control center**:

#### **🏢 Schema/Company Code**
- Enter your company identifier (e.g., `DUKE`, `REU`, `AMEREN`)
- This will be used in the final filename: `DUKE_1072_ib.js`

#### **🎯 Callout Type Selection**
- **9 predefined types** available:
  - `1001` - Employee PIN Verification
  - `1025` - Emergency Callout Response
  - `1072` - General IVR Menu
  - `1006` - Notification Only
  - `2025` - Fill Shift Callout
  - `2050` - Test Callout
  - `2100` - REU Notification
  - And more...

#### **🤖 Auto-Detection**
- When you upload a PDF, the system **automatically suggests** the best callout type
- You'll see "🎯 Auto-detected from PDF content" if the system is confident
- You can still override the suggestion manually

### **2. Multi-Page PDF Processing**

#### **📄 What Happens When You Upload a PDF**

1. **Intelligent Page Analysis**: Each page is classified as:
   - `diagram` - Contains flowchart content
   - `title` - Title page or cover
   - `text` - Text-only content
   - `blank` - Empty or near-empty page
   - `mixed` - Contains both text and potential diagrams

2. **Smart Filtering**: The system automatically **skips**:
   - Title pages
   - Blank pages  
   - Text-only pages
   - Pages with confidence < 30%

3. **Diagram Extraction**: Only valid diagram pages are processed

#### **📊 Example Processing Log**
```
Processing PDF with 13 pages
Page 1: title (diagram: False, confidence: 0.70)     → SKIPPED
Page 2: diagram (diagram: True, confidence: 0.85)    → PROCESSED
Page 3: diagram (diagram: True, confidence: 0.92)    → PROCESSED
Page 4: text (diagram: False, confidence: 0.60)      → SKIPPED
...
Successfully extracted 8 diagrams from 13 pages
```

### **3. Multi-Callout Workflow**

#### **🔄 When You Have Different Callout Types in One PDF**

**Recommended Approach:**

1. **Upload PDF**: The system will extract all valid diagrams
2. **Review Detected Types**: Check the "View All Extracted Diagrams" section
3. **Process Each Diagram Separately**:
   - Select first diagram
   - Verify/adjust callout type and schema
   - Generate IVR code → Download (e.g., `DUKE_1025_ib.js`)
   - Select second diagram  
   - Adjust callout type and schema for this diagram
   - Generate IVR code → Download (e.g., `DUKE_2050.js`)
   - Repeat for each diagram

#### **📝 Example Multi-Callout Session**

```
1. Upload PDF with 13 pages
   → System finds 8 diagrams, skips 5 title/text pages

2. Select "Page 3: Employee Verification (Type: 1001, Confidence: 0.9)"
   → Set Schema: "DUKE", Type: "1001 - Employee PIN Verification" 
   → Generate → Download: DUKE_1001_ib.js

3. Select "Page 7: Test Callout (Type: 2050, Confidence: 0.8)"
   → Set Schema: "DUKE", Type: "2050 - Test Callout"
   → Generate → Download: DUKE_2050.js

4. Select "Page 12: REU Notification (Type: 2100, Confidence: 0.7)"
   → Set Schema: "REU", Type: "2100 - REU Notification"  
   → Generate → Download: REU_2100.js
```

### **4. Enhanced Features**

#### **🧠 Intelligent Content Analysis**
- **Keyword Detection**: Looks for "test", "PIN", "emergency", "REU", etc.
- **Context Understanding**: Analyzes flow structure and decision points
- **Confidence Scoring**: Rates how certain the system is about page classification

#### **📊 Rich Metadata Display**
Each extracted diagram shows:
- **Page Number**: Where it was found
- **Title**: Auto-extracted from content
- **Callout Type**: AI-suggested type
- **Confidence**: How certain the AI is (0.0-1.0)

#### **⚡ Performance Improvements**
- **Faster Processing**: Skips non-diagram pages
- **Better Quality**: Focuses AI processing on actual diagrams
- **Error Resilience**: Graceful fallback if page processing fails

### **5. Error Handling & Troubleshooting**

#### **🔧 Fixed Issues**
- ✅ **Tuple Error Fixed**: No more `'tuple' object has no attribute 'get'`
- ✅ **Smart Fallbacks**: If vector processing fails, falls back to image processing
- ✅ **Page Classification**: Automatically skips problematic pages

#### **📋 What the Logs Tell You**

**Good Processing:**
```
Page 2: diagram (diagram: True, confidence: 0.85)
Successfully extracted diagram from page 2
```

**Skipped Pages:**
```
Page 1: title (diagram: False, confidence: 0.70)
Page 4: blank (diagram: False, confidence: 0.90)
```

**Fallback Processing:**
```
Error processing page 3: vector extraction failed
Using fallback image processing for page 3
```

### **6. Best Practices**

#### **📚 For Multi-Page PDFs**
1. **Let the system filter pages first** - don't worry about title pages
2. **Review all extracted diagrams** before processing
3. **Set appropriate schema/callout type for each diagram**
4. **Process similar diagrams in batches** for efficiency

#### **🎯 For Callout Type Selection**
1. **Trust the auto-detection** for common patterns
2. **Override when you know better** (you're the expert!)
3. **Use custom callout IDs** for organization-specific types
4. **Set schema consistently** across related diagrams

#### **💾 For File Organization**
1. **Use descriptive schemas** (company codes work best)
2. **Let the system generate filenames** automatically
3. **Download immediately** after generation
4. **Keep track of which page corresponds to which file**

## 🚀 **Summary**

The enhanced system now handles your real-world scenario perfectly:

- ✅ **13-page PDFs**: Processes efficiently, skips irrelevant pages
- ✅ **Multiple Callout Types**: Each diagram can have its own type
- ✅ **Title Page Filtering**: Automatically skips title screens
- ✅ **Professional File Naming**: `${SCHEMA}_${CALLOUT_TYPE_ID}[_ib].js`
- ✅ **Smart Auto-Detection**: Suggests appropriate callout types
- ✅ **Error Resilient**: Graceful handling of problematic pages

**Your workflow is now: Upload PDF → Review extracted diagrams → Configure each → Generate & Download**

No more manual page filtering, no more tuple errors, and full support for complex multi-callout documents!