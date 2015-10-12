# Script for creating NCBI Taxonomy database tables.
# Done according to .readme files from NCBI FTP.
#
CREATE TABLE division
(
#Divisions file (division.dmp):
#	division id				-- taxonomy database division id
    division_id INTEGER UNSIGNED NOT NULL,
    PRIMARY KEY (division_id),
#	division cde				-- GenBank division code (three characters)
    division_cde VARCHAR(4),
#	division name				-- e.g. BCT, PLN, VRT, MAM, PRI...
    division_name TEXT,
#	comments
    comments TEXT
) ENGINE=InnoDB;

CREATE TABLE gencode
(
#Genetic codes file (gencode.dmp):
#	genetic code id				-- GenBank genetic code id
    genetic_code_id INTEGER UNSIGNED NOT NULL,
    PRIMARY KEY (genetic_code_id),
#	abbreviation				-- genetic code name abbreviation
    abbreviation TEXT,
#	name					-- genetic code name
    name TEXT,
#	cde					-- translation table for this genetic code
    cde TEXT,
#	starts					-- start codons for this genetic code
    starts TEXT
) ENGINE=InnoDB;

CREATE TABLE nodes
(
#nodes.dmp file consists of taxonomy nodes. The description for each node includes the following
#fields:
#	tax_id					-- node id in GenBank taxonomy database
    tax_id INTEGER UNSIGNED NOT NULL,
    PRIMARY KEY (tax_id),
# 	parent tax_id				-- parent node id in GenBank taxonomy database
    parent_tax_id INTEGER UNSIGNED NOT NULL,
# 	rank					-- rank of this node (superkingdom, kingdom, ...) 
    rank VARCHAR(20) NOT NULL,
# 	embl code				-- locus-name prefix; not unique
    embl_code VARCHAR(5),
# 	division id				-- see division.dmp file
    division_id INTEGER UNSIGNED NOT NULL,
    INDEX (division_id),
    FOREIGN KEY (division_id) REFERENCES division(division_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
# 	inherited div flag  (1 or 0)		-- 1 if node inherits division from parent
    inherited_div_flag BOOL NOT NULL,
# 	genetic code id				-- see gencode.dmp file
    genetic_code_id INTEGER UNSIGNED NOT NULL,
    FOREIGN KEY (genetic_code_id) REFERENCES gencode(genetic_code_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
# 	inherited GC  flag  (1 or 0)		-- 1 if node inherits genetic code from parent
    inhericed_gc_flag BOOL NOT NULL,
# 	mitochondrial genetic code id		-- see gencode.dmp file
    mitochondrial_genetic_code_id BOOL NOT NULL,
# 	inherited MGC flag  (1 or 0)		-- 1 if node inherits mitochondrial gencode from parent
    inherited_mgc_flag BOOL NOT NULL,
# 	GenBank hidden flag (1 or 0)            -- 1 if name is suppressed in GenBank entry lineage
    genbank_hidden_flag BOOL NOT NULL,
# 	hidden subtree root flag (1 or 0)       -- 1 if this subtree has no sequence data yet
    hidden_subtree_root_flag BOOL NOT NULL,
# 	comments				-- free-text comments and citations
    comments TEXT
) ENGINE=InnoDB;

CREATE TABLE names
(
#Taxonomy names file (names.dmp):
#	tax_id					-- the id of node associated with this name
    tax_id INTEGER UNSIGNED NOT NULL,
    INDEX (tax_id),
    FOREIGN KEY (tax_id) REFERENCES nodes(tax_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
#	name_txt				-- name itself
    name_txt TEXT,
#	unique name				-- the unique variant of this name if name not unique
    unique_name TEXT,
#	name class				-- (synonym, common name, ...)
    name_class ENUM(
        'acronym',
        'anamorph',
        'authority',
        'blast name',
        'common name',
        'equivalent name',
        'genbank acronym',
        'genbank anamorph',
        'genbank common name',
        'genbank synonym',
        'includes',
        'in-part',
        'misnomer',
        'misspelling',
        'scientific name',
        'synonym',
        'teleomorph',
        'type material')
) ENGINE=InnoDB;

CREATE TABLE delnodes
(
#Deleted nodes file (delnodes.dmp):
#	tax_id					-- deleted node id
    tax_id INTEGER UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE TABLE merged
(
#Merged nodes file (merged.dmp):
#	old_tax_id                              -- id of nodes which has been merged
    old_tax_id INTEGER UNSIGNED NOT NULL,
#	new_tax_id                              -- id of nodes which is result of merging
    new_tax_id INTEGER UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE TABLE citations
(
#Citations file (citations.dmp):
#	cit_id					-- the unique id of citation
    cit_id INTEGER UNSIGNED NOT NULL,
#	cit_key					-- citation key
    cit_key TEXT,
#	pubmed_id				-- unique id in PubMed database (0 if not in PubMed)
    pubmed_id INTEGER UNSIGNED NOT NULL DEFAULT 0,
#	medline_id				-- unique id in MedLine database (0 if not in MedLine)
    medline_id INTEGER UNSIGNED NOT NULL DEFAULT 0,
#	url					-- URL associated with citation
    url TEXT,
#	text					-- any text (usually article name and authors).
#						-- The following characters are escaped in this text by a backslash:
#						-- newline (appear as "\n"),
#						-- tab character ("\t"),
#						-- double quotes ('\"'),
#						-- backslash character ("\\").
    citation_text TEXT,
#	taxid_list				-- list of node ids separated by a single space
    taxid_list MEDIUMTEXT
    # Should be many-to-many relationship in separate table?
) ENGINE=InnoDB;
