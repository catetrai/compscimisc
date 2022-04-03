# The Confluence index journal

## What is the journal?

In Confluence, each Lucene index has a journal that logs changes to content (e.g. page created, updated, likes, comments, ...).

**The journal system allows Confluence to check if the index is missing, stale or corrupt.** This is particularly important in a Confluence Data Center cluster, where each node must keep its own local indexes in sync.

When a Confluence node starts, it checks the state of its indexes. It does so by comparing the latest **journal entry ID** stored in the **database** with the journal entry ID stored in a **file in the home directory**.If the two don't match, Confluence will try to rebuild the index (or recover it from another node in the cluster or from the shared home index backup).

## Journal entries in the database

Changes to Confluence content that need to be indexed are logged in the `JOURNALENTRY` database table.

Each journal entry has a numeric ID, which is stored in the primary key column `entry_id`.

Here is an SQL query to display the last 10 journal entries:

```sql
SELECT entry_id, journal_name, creationdate, type, message
	FROM public.journalentry ORDER BY entry_id DESC LIMIT 10;
```
Result:

| "entry_id" | "journal_name" | "creationdate"            | "type"                                 | "message"                                                                                                                           |
|------------|----------------|---------------------------|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| 2747       | "main_index"   | "2020-06-26 12:06:45.826" | "UPDATE_DOCUMENT"                      | "com.atlassian.confluence.user.PersonalInformation-360562"                                                                          |
| 2746       | "edge_index"   | "2020-06-25 17:46:10.48"  | "ADD_DOCUMENT"                         | "{"edgeId":"8847363","userKey":"8a8180d16eeb899b01725f3b3aee01b8","targetId":8847363,"date":1593099970397,"typeKey":"page.create"}" |
| 2745       | "main_index"   | "2020-06-25 17:46:10.41"  | "UPDATE_DOCUMENT_EXCLUDING_DEPENDENTS" | "com.atlassian.confluence.pages.Page-8847363"                                                                                       |
| 2744       | "main_index"   | "2020-06-25 17:46:10.409" | "ADD_CHANGE_DOCUMENT"                  | "com.atlassian.confluence.pages.Page-8847363"                                                                                       |
| 2743       | "main_index"   | "2020-06-25 17:46:10.398" | "UPDATE_DOCUMENT"                      | "com.atlassian.confluence.pages.Page-8847363"                                                                                       |
| 2742       | "main_index"   | "2020-06-25 17:46:10.398" | "ADD_CHANGE_DOCUMENT"                  | "com.atlassian.confluence.pages.Page-8847363"                                                                                       |
| 2741       | "main_index"   | "2020-06-25 17:45:49.688" | "UPDATE_DOCUMENT"                      | "com.atlassian.confluence.pages.Page-7798922"                                                                                       |
| 2740       | "main_index"   | "2020-06-25 17:45:49.686" | "ADD_CHANGE_DOCUMENT"                  | "com.atlassian.confluence.pages.Page-7798922"                                                                                       |
| 2739       | "main_index"   | "2020-06-25 17:45:49.685" | "ADD_CHANGE_DOCUMENT"                  | "com.atlassian.confluence.pages.Page-8847361"                                                                                       |
| 2738       | "edge_index"   | "2020-06-25 17:42:43.579" | "ADD_DOCUMENT"                         | "{"edgeId":"7798922","userKey":"8a8180d16eeb899b01725f3b3aee01b8","targetId":7798922,"date":1593098225370,"typeKey":"page.create"}" |


<br>

These are some of the types of events that will be logged in the journal:

```sql
SELECT type FROM public.journalentry GROUP BY type ORDER BY type ASC;
```

| "type"                                 |
|----------------------------------------|
| "ADD_CHANGE_DOCUMENT"                  |
| "ADD_DOCUMENT"                         |
| "DELETE_CHANGE_DOCUMENTS"              |
| "DELETE_DOCUMENT"                      |
| "DELETE_EDGE_TARGETING_DOCUMENT"       |
| "UPDATE_DOCUMENT"                      |
| "UPDATE_DOCUMENT_EXCLUDING_DEPENDENTS" |

<br>

In the table we can also see there are 2 journal names, `main_index` and `edge_index`. These are journals for the two Lucene indexes that Confluence keeps (presumably for searching _nodes_ and _edges_ of the content graph?).

So what are these journal entries good for?

## The journal state store

In the Confluence home directory on the filesystem, there is a directory called `journal/` which stores a text file for each journal type:

```bash
trainit.cat@SVL0110:~$ sudo ls -la /var/atlassian/application-data/confluence/journal
total 16
...
-rw-r-----  1 confluence1 confluence1    4 Jun 25 17:46 edge_index
-rw-r-----  1 confluence1 confluence1    4 Jun 26 12:06 main_index
```

These should contain exactly the latest journal entry ID that has been committed in the database for that index. For the main index, we have:

```bash
trainit.cat@SVL0110:~$ sudo cat /var/atlassian/application-data/confluence/journal/main_index
2747
```

In a Confluence Data Center installation with >2 nodes, each node stores these files in its own local home directory (same as the index). The files are updated every few seconds seconds, as we can see by comparing the `creationdate` of the table row with the modification time of the file:

```sql
SELECT entry_id, journal_name, creationdate
	FROM public.journalentry WHERE entry_id = 2760;
```

| "entry_id" | "journal_name" | "creationdate"            |
|------------|----------------|---------------------------|
| 2760       | "main_index"   | "2020-06-27 12:13:16.288" |


<br>

To check file modification time in UNIX systems (`mtime`), we can use the `stat` command:

```bash
trainit.cat@SVL0110:~$ sudo stat /var/atlassian/application-data/confluence/journal/main_index
...
Modify: 2020-06-27 12:13:21.398970620 +0200
...
```

## Corruption of the journal

It can happen that the journal ID stored in the file gets out of sync (or in an otherwise inconsistent relationship) with the database ID.

To check for this, before writing the new database ID to the file Confluence will compare the two IDs. If the new database ID is _lower_ that the current ID on file, then this error message will be thrown in `atlassian-confluence.log`:

```
2020-05-14 10:44:11,989 WARN [http-nio-8090-exec-2] [confluence.impl.journal.DefaultJournalManager] enqueue Newly enqueued entry in journal [main_index] has an ID [27] that should have been higher than the journal state store's most-recent-id [6493]. it is likely that this node's journal state store is corrupt.
```

where the _journal state store_ is the file in the home directory.

What is the cause of this inconsistency? Well, it can either be in the database or in the filesystem:

- If the database is not generating sequential IDs (with an increment of 1), then there can be 'jumps' from one ID to the next, or even IDs created in the wrong order. This behaviour is controlled by the _sequence definition_ for the database sequence `seq_journal_entry_id`. Below is the CREATE script for the sequence. Important here is the `CACHE` value: if it is not 1, then IDs could be generated in non-sequential order.

```sql
CREATE SEQUENCE public.seq_journal_entry_id
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;
```

- If the journal file is corrupt for any reason (e.g. permissions, or I/O error, or was tampered with), then the latest logged ID might be incorrect. Here, the solution is to simply stop Confluence, remove the whole `journal/` directory _and_ the whole `index/` directory, and let Confluence re-build the index and the journal files upon startup. Then you can also trigger a reindexing through the admin UI.

Here is the full Atlassian KB article for fixing this problem: [Index not working due to 'journal state store is corrupt' error](https://confluence.atlassian.com/confkb/index-not-working-due-to-journal-state-store-is-corrupt-error-687023405.html)

## Open questions

1. What component of Confluence is responsible for writing to the journal state store (file in the home directory)?
2. Does the journal get updated whenever a new journal entry is stored in the database, or when an event is indexed in Lucene?

## References

- All the secrets of the Confluence search index: [Searching and Indexing Troubleshooting](https://confluence.atlassian.com/confkb/searching-and-indexing-troubleshooting-180847237.html)
- Indexing in a Confluence Data Center cluster: [Clustering with Confluence Data Center](https://confluence.atlassian.com/doc/clustering-with-confluence-data-center-790795847.html#ClusteringwithConfluenceDataCenter-Indexes)
- Journal Service API (developer docs): [Confluence Journal Service](https://developer.atlassian.com/server/confluence/confluence-journal-service/)