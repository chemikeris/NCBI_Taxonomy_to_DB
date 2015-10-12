#! /usr/bin/env python
"""Load NCBI Taxonomy data from dump files to MySQL database.

Usage:
    --db       : name of database;
    --host     : database host;
    --user     : database username;
    --password : database password;
    --directory: directory for downloading and processing data ;
    --download : force download of data dumps from NCBI FTP server;
-h, --help     : print this message.

DB-related settings (database name, username, password, host) can be provided
in file settings.py instead of giving them from command line.
"""

import sys
import os
import tempfile
import getopt
import logging
import shutil
import zipfile
import urllib2
try:
    import MySQLdb
except ImportError, err:
    sys.stderr.write(
        'This script depends on MySQLdb module, which was not found.')
    sys.exit(1)


def download_taxdump_to(directory):
    """Retrieve taxdump files from NCBI FTP"""
    filename = 'taxdmp.zip'
    source_url = 'ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/%s' % filename
    result_file_with_path = os.path.join(directory, filename)
    try:
        logging.info('Trying to download from %s', source_url)
        connection_to_ncbi = urllib2.urlopen(source_url)
    except urllib2.URLError, err:
        logging.error('Connecting to NCBI FTP failed: %s', err)
        logging.debug('Reason: %s', err.reason)
        return False
    else:
        with open(result_file_with_path, 'w') as f:
            f.write(connection_to_ncbi.read())
        logging.info('Successfully...')
        connection_to_ncbi.close()
        unzip_taxdump_files(directory)
        return True


def unzip_taxdump_files(directory):
    """Unzip file taxdmp.zip in given directory"""
    logging.info('Unzipping dump files in %s', directory)
    filename = os.path.join(directory, 'taxdmp.zip')
    with zipfile.ZipFile(filename) as zf:
        for fname in zf.namelist():
            zf.extract(fname, directory)


def dump_files_do_not_exist_in(directory):
    """Checks if necessary taxonomy dump files exist in given directory"""
    expected_files = (
        'citations.dmp',
        'delnodes.dmp',
        'division.dmp',
        'gencode.dmp',
        'merged.dmp',
        'names.dmp',
        'nodes.dmp')
    all_dmp_files_present = True
    for fname in expected_files:
        if os.path.isfile(os.path.join(directory, fname)):
            continue
        else:
            all_dmp_files_present = False
            logging.debug('File %s is missing', fname)
    if all_dmp_files_present:
        # Files do exists, returning False
        return False
    else:
        zipped_file = os.path.join(directory, 'taxdmp.zip')
        logging.debug('Searching for zipped file %s', zipped_file)
        if os.path.isfile(zipped_file):
            logging.debug('Found!')
            unzip_taxdump_files(directory)
            return False
        else:
            logging.warning('Necessary files not found in %s', directory)
            return True


def prepare_database(db):
    """Get connection to empty MySQL DB for loading NCBI taxonomy"""
    logging.info("Re-creating NCBI taxonomy DB in '%s'", db['name'])
    connection_for_preparing_db = MySQLdb.connect(
        host=db['host'], user=db['user'], passwd=db['password'])
    preparing_db_cursor = connection_for_preparing_db.cursor()
    logging.debug('Dropping...')
    preparing_db_cursor.execute("DROP DATABASE IF EXISTS %s" % db['name'])
    logging.debug('Creating empty DB...')
    preparing_db_cursor.execute("CREATE DATABASE %s" % db['name'])
    connection_for_preparing_db.close()

    db_connection = MySQLdb.connect(
        host=db['host'], user=db['user'], passwd=db['password'], db=db['name'])
    logging.debug('Creating tables...')
    cursor = db_connection.cursor()
    cursor.execute("""
        CREATE TABLE division
        (
            division_id INTEGER UNSIGNED NOT NULL,
            PRIMARY KEY (division_id),
            division_cde VARCHAR(4),
            division_name TEXT,
            comments TEXT
        ) ENGINE=InnoDB;

        CREATE TABLE gencode
        (
            genetic_code_id INTEGER UNSIGNED NOT NULL,
            PRIMARY KEY (genetic_code_id),
            abbreviation TEXT,
            name TEXT,
            cde TEXT,
            starts TEXT
        ) ENGINE=InnoDB;

        CREATE TABLE nodes
        (
            tax_id INTEGER UNSIGNED NOT NULL,
            PRIMARY KEY (tax_id),
            parent_tax_id INTEGER UNSIGNED NOT NULL,
            rank VARCHAR(20) NOT NULL,
            embl_code VARCHAR(5),
            division_id INTEGER UNSIGNED NOT NULL,
            INDEX (division_id),
            FOREIGN KEY (division_id) REFERENCES division(division_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            inherited_div_flag BOOL NOT NULL,
            genetic_code_id INTEGER UNSIGNED NOT NULL,
            FOREIGN KEY (genetic_code_id) REFERENCES gencode(genetic_code_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            inhericed_gc_flag BOOL NOT NULL,
            mitochondrial_genetic_code_id BOOL NOT NULL,
            inherited_mgc_flag BOOL NOT NULL,
            genbank_hidden_flag BOOL NOT NULL,
            hidden_subtree_root_flag BOOL NOT NULL,
            comments TEXT
        ) ENGINE=InnoDB;

        CREATE TABLE names
        (
            tax_id INTEGER UNSIGNED NOT NULL,
            INDEX (tax_id),
            FOREIGN KEY (tax_id) REFERENCES nodes(tax_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            name_txt TEXT,
            unique_name TEXT,
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
            tax_id INTEGER UNSIGNED NOT NULL
        ) ENGINE=InnoDB;

        CREATE TABLE merged
        (
            old_tax_id INTEGER UNSIGNED NOT NULL,
            new_tax_id INTEGER UNSIGNED NOT NULL
        ) ENGINE=InnoDB;

        CREATE TABLE citations
        (
            cit_id INTEGER UNSIGNED NOT NULL,
            cit_key TEXT,
            pubmed_id INTEGER UNSIGNED NOT NULL DEFAULT 0,
            medline_id INTEGER UNSIGNED NOT NULL DEFAULT 0,
            url TEXT,
            citation_text TEXT,
            taxid_list MEDIUMTEXT
            # Should be many-to-many relationship in separate table?
        ) ENGINE=InnoDB; """)
    return db_connection


def ncbi_taxonomy_to_sql(
        db, directory, download_data_from_ncbi, cleanup_data_directory,
        **unused_kwargs):
    """Load newest NCBI taxonomy database from given dump files"""
    logging.info('Starting loading NCBI Taxonomy data to database.')
    if download_data_from_ncbi or dump_files_do_not_exist_in(directory):
        dump_files_exist = download_taxdump_to(directory)
    else:
        dump_files_exist = True
    if dump_files_exist:
        db = prepare_database(db)
        cursor = db.cursor()
        tables_list = (
            'division', 'gencode', 'nodes', 'names', 'delnodes', 'merged',
            'citations')
        for table_name in tables_list:
            logging.info('Loading table %s', table_name)
            dump_file = os.path.join(directory, '%s.dmp' % table_name)
            cursor.execute(
                """ LOAD DATA LOCAL INFILE %%s INTO TABLE %s
                    FIELDS TERMINATED BY '\t|\t'
                    LINES TERMINATED BY '\t|\n'""" % table_name,
                (dump_file,))
        db.commit()
        data_loaded_successfully = True
    else:
        data_loaded_successfully = False

    if cleanup_data_directory:
        shutil.rmtree(directory)
    if data_loaded_successfully:
        logging.info('Data loaded successfully.')
        return 0
    else:
        logging.info('Data loading failed.')
        return 1


def set_logging(arguments):
    if '--debug' in arguments:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)


def parse_options(arguments):
    """Parse command line options"""
    parsed_options = {}
    parsed_options['db'] = {}
    try:
        import settings
    except ImportError, err:
        logging.debug('settings.py not imported: %s', err)
        parsed_options['db']['name'] = 'ncbi_taxonomy'
        parsed_options['db']['host'] = 'localhost'
        parsed_options['db']['user'] = None
        parsed_options['db']['password'] = None
    else:
        try:
            parsed_options['db']['name'] = settings.db_name
            parsed_options['db']['host'] = settings.db_host
            parsed_options['db']['user'] = settings.db_user
            parsed_options['db']['password'] = settings.db_password
        except AttributeError, err:
            sys.stderr.write(
                'Incorrect settings in file settings.py: %s\n' % err)
            return None
    data_directory = None
    parsed_options['download_data_from_ncbi'] = False

    try:
        options, remaining_argv = getopt.gnu_getopt(
            arguments[1:],
            'h',
            ['help', 'debug', 'db=', 'host=', 'user=', 'password=',
             'directory=', 'download']
            )
    except getopt.GetoptError, err:
        sys.stderr.write(
            'ERROR: getting command line options failed: %s' % err)
        return None
    else:
        for opt, arg in options:
            if opt in ('-h', '--help'):
                print __doc__
                return None
            elif opt == '--db':
                parsed_options['db']['name'] = arg
            elif opt == '--host':
                parsed_options['db']['host'] = arg
            elif opt == '--user':
                parsed_options['db']['user'] = arg
            elif opt == '--password':
                parsed_options['db']['password'] = arg
            elif opt == '--directory':
                data_directory = arg
            elif opt == '--download':
                parsed_options['download_data_from_ncbi'] = True

    # If database user or password are not given, exiting.
    if (parsed_options['db']['user'] is None) or \
            (parsed_options['db']['password'] is None):
        logging.error(
            'Please provide DB username and password, either from '\
            'command line arguments or in settings.py')
        return None
    # If data directory is not given, the downloading data to temporary dir.
    if data_directory is None:
        logging.info(
            'Data directory not given, downloading files from NCBI '\
            'to a temporary directory.')
        data_directory = tempfile.mkdtemp()
        parsed_options['cleanup_data_directory'] = True
        parsed_options['download_data_from_ncbi'] = True
    else:
        parsed_options['cleanup_data_directory'] = False
    parsed_options['directory'] = data_directory

    return parsed_options


def main(arguments):
    set_logging(arguments)
    options = parse_options(arguments)
    if options is None:
        return 1
    else:
        return ncbi_taxonomy_to_sql(**options)


if __name__ == '__main__':
    sys.exit(main(sys.argv))

