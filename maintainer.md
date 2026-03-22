
---

# 📖 Content Maintainer Guide: Decision Engine

This guide explains how to use the **Admin Dashboard** to build and update the decision tree without touching any code.

## 🚀 Getting Started
To manage the content, open your web browser and navigate to:
`http://localhost:5000/admin` (or your hosted website URL followed by `/admin`).



---

## 🏗️ The Anatomy of a "Node"
Every page the user sees is called a **Node**. There are two types of nodes:
1.  **Question Node:** Asks the user a question and provides buttons to lead them to the next step.
2.  **Result Node:** The "End" of a path. It shows a final message and allows the user to download their results.

### Each Node has three parts:
* **Unique ID:** A short, one-word name (e.g., `start`, `apply_now`, `step2`). **Never use spaces.**
* **Heading Text:** The main question or title shown at the top of the page.
* **Description:** The detailed explanation. You can use **Markdown** here:
    * `**Bold Text**` becomes **Bold Text**.
    * `[Click Here](https://google.com)` creates a clickable link.
    * Use a dash `-` at the start of a line to create a bulleted list.

---

## ➕ Creating and Editing
### How to add a new Question:
1.  Click the **+ New Node** button on the Dashboard.
2.  Give it a **Unique ID**.
3.  Type your **Heading** and **Description**.
4.  Under **Buttons / Pathing**, click **+ Add Option**.
    * **Label:** What the button says (e.g., "Yes, I agree").
    * **Target ID:** The **Unique ID** of the page this button should link to.
5.  Click **Save**.



### How to create an End/Result:
To make a page the final stop, simply **delete all options/buttons**. When a node has no buttons, the system automatically shows the "Workflow Complete" message and the Download PDF/TXT buttons.

---

## 🛠️ Validation and Safety
The system includes a built-in safety checker to prevent the website from breaking.

### Broken Link Warnings
If you see a red box at the top of the Admin Dashboard saying **"Validation Errors,"** it means a button is pointing to a **Target ID** that does not exist. 
* **Fix:** Either create a new node with that missing ID or edit the existing node to point to a correct ID.

### Backing Up
Before making major changes, click the **Backup JSON** button. This downloads a file named `questions_backup.json`. If anything goes wrong, a developer can use this file to restore the previous version of the site.

---

## 💡 Pro-Tips for a Better Workflow
* **Plan on paper:** Draw your "tree" on a piece of paper or a whiteboard before typing it into the system.
* **Start with "start":** The website always begins at the node with the ID `start`. Do not delete or rename the `start` node.
* **Live View:** After clicking **Save**, click the **Live View** button to immediately test how your changes look to the end-user.

---

**Would you like me to create a "Cheat Sheet" of Markdown commands for the maintainers to keep on their desks?**
